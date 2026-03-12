import cv2                           
import numpy as np                   
import time                          
import subprocess                    
import os                            

SERIAL_DEV = "/dev/ttyUSB0"          
BAUD = "115200"                      

def setup_serial(dev, baud):
    """Configura el puerto serie (8N1, sin control de flujo)."""
    subprocess.run(["stty", "-F", dev, baud, "cs8", "-cstopb", "-parenb", "-ixon", "-ixoff"], check=True)

def open_serial(dev):
    """Abre el puerto serie en modo binario, sin buffer (escritura inmediata)."""
    return open(dev, "wb", buffering=0)

URL = "rtsp://192.168.1.10:554/user=admin_password=tlJwpbo6_channel=1_stream=0.sdp?real_stream"

os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;5000000|max_delay;0"

def abrir_rtsp(url):
    """Intenta abrir el stream RTSP con reintentos hasta 5 segundos."""
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)    
    t0 = time.time()
    while time.time() - t0 < 5:                    
        if cap.isOpened():
            ok, f = cap.read()
            if ok and f is not None:
                return cap                         
        time.sleep(0.1)
    cap.release()
    return None

def procesar(video_path):
    """Procesa un clip MP4 grabado y calcula el promedio del nivel detectado."""
    cap = cv2.VideoCapture(video_path)             
    height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)    
    width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)      
    print(f"Resolución original del clip: {width}x{height}")

    tp = 0                                         
    filtro_bajo = 150                              
    valor_dia = 19242                              
    niveles = []                                   

    cv2.namedWindow("Filtro", cv2.WINDOW_NORMAL)
    cv2.namedWindow("MASCARA", cv2.WINDOW_NORMAL)

    while cap.isOpened():                          
        ret, frame = cap.read()                   
        if not ret:
            break                                  

        frame = cv2.resize(frame, (640, 480))      

        m = np.zeros(frame.shape[:2], np.uint8)    
        cv2.rectangle(m, (305, 29), (350, 480), (255, 255, 255), -1)  
        m2 = np.zeros(frame.shape[:3], np.uint8)   
        cv2.rectangle(m2, (303, 29), (353, 480), (255, 255, 255), -1)
        h2 = m2 & frame                            
        h = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV) 

        if tp < valor_dia:                         
            f1 = cv2.cvtColor(h2, cv2.COLOR_BGR2GRAY)
            ret, f1 = cv2.threshold(f1, filtro_bajo, 255, cv2.THRESH_BINARY_INV)
            kernel3 = np.ones((25, 25), np.uint8)
            kernel4 = np.ones((25, 25), np.uint8)
            f1 = cv2.morphologyEx(f1, cv2.MORPH_OPEN, kernel4)
            f1 = cv2.morphologyEx(f1, cv2.MORPH_CLOSE, kernel3)
            px = 1275                              
        else:                                      
            f1 = cv2.inRange(h, (0, 0, 0), (179, 255, 38))
            px = 1300                              

        kernel = np.ones((20, 20), np.uint8)
        kernel2 = np.ones((150, 150), np.uint8)
        f1 = cv2.morphologyEx(f1, cv2.MORPH_CLOSE, kernel)
        f1 = cv2.morphologyEx(f1, cv2.MORPH_OPEN, kernel2)
        m_mask = f1 & m                            
        nivel = f1 & m                             

        ret, thresh = cv2.threshold(nivel, 127, 255, cv2.THRESH_OTSU)
        contours, hierarchy = cv2.findContours(thresh.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        try:
            cnt = contours[0]                      
            tp += 1
        except:
            if (cv2.getWindowProperty("Filtro", cv2.WND_PROP_VISIBLE) < 1 or
                cv2.getWindowProperty("MASCARA", cv2.WND_PROP_VISIBLE) < 1):
                break
            continue

        area = cv2.contourArea(cnt)               
        niv = ((area * 10) / px) + 40             
        niv = round(niv, 1)
        niveles.append(niv)                        
        print("Nivel instantáneo:", niv, "cm")

        if len(contours) > 0:
            cv2.putText(frame, 'Nivel', (400, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
            cv2.putText(frame, str(niv), (420, 110), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 3)
            cv2.putText(frame, "cm", (530, 110), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 3)
            cv2.rectangle(frame, (305, 29), (350, 480), (255, 0, 0), 2)
            cv2.imshow("Filtro", frame)
            cv2.imshow("MASCARA", m_mask)

        if (cv2.waitKey(1) & 0xFF) == ord('q'):
            break
        if (cv2.getWindowProperty("Filtro", cv2.WND_PROP_VISIBLE) < 1 or
            cv2.getWindowProperty("MASCARA", cv2.WND_PROP_VISIBLE) < 1):
            break

    cap.release()
    cv2.destroyAllWindows()

    if len(niveles) > 0:
        promedio = round(sum(niveles) / len(niveles), 2)
        print("==== PROMEDIO:", promedio, "cm ====")
        return promedio
    else:
        print("No se detectaron niveles en el clip")
        return None

def main():
    """Captura 10 segundos desde la cámara IP, procesa el clip y envía el promedio a la Heltec."""
    setup_serial(SERIAL_DEV, BAUD)
    ser = open_serial(SERIAL_DEV)
    print("Serial listo hacia Heltec TX")

    try:
        while True:
            cap = abrir_rtsp(URL)
            if not cap:
                print("No se pudo abrir la cámara IP. Reintentando en 10 s...")
                time.sleep(10)
                continue

            fps = 30                             
            width, height = 640, 480            

            out = cv2.VideoWriter(
                "canal.mp4",
                cv2.VideoWriter_fourcc(*'mp4v'),
                fps,
                (width, height)
            )

            print("Grabando 10 segundos desde la cámara IP...")
            inicio = time.time()
            while (time.time() - inicio) < 10.0:
                ok, frame = cap.read()
                if not ok or frame is None:
                    continue
                frame = cv2.resize(frame, (width, height))   
                out.write(frame)

            cap.release()
            out.release()
            print("Grabación lista: canal.mp4")

            promedio = procesar("canal.mp4")

            if promedio is not None:
                linea = f"{promedio:.2f}\n".encode("ascii")
                ser.write(linea)
                print("TX promedio Heltec:", linea.decode().strip(), "cm")

            print("Esperando 10 minutos para la próxima grabación...")
            time.sleep(600)                     

    except KeyboardInterrupt:
        print("\nFin del programa.")
    finally:
        try:
            ser.close()                         
        except:
            pass

if __name__ == "__main__":
    main()