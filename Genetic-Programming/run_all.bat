@echo off
cd /d "%~dp0"
echo Starting Python Backend...
start "Python-Backend" /min python -m uvicorn main:aplicacion_servidor_web --port 8000
echo Starting Java Frontend...
start "Java-Frontend" /min "C:\Users\DELL\.jdks\openjdk-25.0.2\bin\java.exe" -jar "spring-boot-backend/target/genetic-programming-0.0.1-SNAPSHOT.jar"
exit
