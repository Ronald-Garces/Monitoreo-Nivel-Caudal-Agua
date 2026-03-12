import cv2                          
import numpy as np                
import time                         
import subprocess                   

SERIAL_DEV = "/dev/ttyUSB0"         
BAUD = "115200"                     

def setup_serial(dev, baud):
    subprocess.run(["stty", "-F", dev, baud, "cs8", "-cstopb", "-parenb", "-ixon", "-ixoff"], check=True)

def open_serial(dev):
    return open(dev, "wb", buffering=0)

def procesar(video_path):
    cap = cv2.VideoCapture(video_path)                          
    height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)                 
    width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)                   
    size = width, height                                        
    print(size)                                                 

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
        contours, hierarchy = cv2.findContours(                 
            thresh.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
        )
        try:
            cnt = contours[0]                                   
            tp = tp + 1                                         
        except:                                                 
            filtro_visible = cv2.getWindowProperty("Filtro", cv2.WND_PROP_VISIBLE)  
            mascara_visible = cv2.getWindowProperty("MASCARA", cv2.WND_PROP_VISIBLE)
            if (filtro_visible < 1) or (mascara_visible < 1):   
                break                                           
            if (cv2.waitKey(1) & 0xFF) == ord('q'):            
                break                                           
            continue                                            

        area = cv2.contourArea(cnt)                             
        niv = ((area * 10) / px) + 40                           
        niv = round(niv, 1)                                     
        niveles.append(niv)                                     

        print("Nivel instantaneo:", niv, "cm")                  

        if len(contours) > 0:                                   
            cv2.putText(frame, 'Nivel', (400, 50),              
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
            cv2.putText(frame, str(niv), (420, 110),            
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 3)
            cv2.putText(frame, "cm", (530, 110),                
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 3)
            cv2.rectangle(frame, (305, 29), (350, 480),         
                          (255, 0, 0), 2)
            cv2.imshow("Filtro", frame)                         
            cv2.imshow("MASCARA", m_mask)                       

        if (cv2.waitKey(1) & 0xFF) == ord('q'):                 
            break                                               
        filtro_visible = cv2.getWindowProperty("Filtro", cv2.WND_PROP_VISIBLE)  
        mascara_visible = cv2.getWindowProperty("MASCARA", cv2.WND_PROP_VISIBLE) 
        if (filtro_visible < 1) or (mascara_visible < 1):       
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
    setup_serial(SERIAL_DEV, BAUD)                              
    ser = open_serial(SERIAL_DEV)                               
    print("Serial listo hacia Heltec TX")                       

    try:
        while True:                                             
            cap = cv2.VideoCapture(0, cv2.CAP_V4L2)             
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))  
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)              
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)             
            cap.set(cv2.CAP_PROP_FPS, 30)                       

            t0 = time.time()                                    
            first_frame = None                                  
            while time.time() - t0 < 3.0:                       
                ret, f = cap.read()                             
                if ret and f is not None:                       
                    first_frame = f                             
                    break                                       

            if first_frame is None:                             
                print("No se pudo obtener primer frame de la cámara")  
                cap.release()                                   
                print("Esperando 10 minutos para la próxima grabación...")  
                time.sleep(600)                                 
                continue                                        

            fps = 30                                            
            h, w = first_frame.shape[:2]                        

            out = cv2.VideoWriter(                              
                "canal.mp4",                                    
                cv2.VideoWriter_fourcc(*'mp4v'),                
                fps,                                            
                (w, h)                                          
            )

            print("Grabando 10 segundos...")                    
            out.write(first_frame)                              
            grabados = 1                                        

            inicio = time.time()                                
            while (time.time() - inicio) < 10.0:                
                ret, frame = cap.read()                         
                if not ret or frame is None:                    
                    continue                                    
                out.write(frame)                                
                grabados += 1                                   

            cap.release()                                       
            out.release()                                      
            print(f"Grabación lista: canal.mp4 (frames: {grabados})")  

            promedio = procesar("canal.mp4")                    

            if promedio is not None:                            
                linea = f"{promedio:.2f}\n".encode("ascii")     
                ser.write(linea)                                
                print("TX promedio Heltec:", linea.decode().strip(), "cm")  

            
            print("Esperando 10 minutos para la próxima grabación...")  
            time.sleep(60)                                     

    except KeyboardInterrupt:                                   
        print("\nFin.")                                         
    finally:
        try:
            ser.close()                                         
        except:
            pass                                                

if __name__ == "__main__":                                      
    main()                                                      