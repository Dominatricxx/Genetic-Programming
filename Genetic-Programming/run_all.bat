@echo off
setlocal
cd /d "%~dp0"

echo [1/3] Verificando dependencias...
set JAVA_PATH="C:\Users\DELL\.jdks\openjdk-25.0.2\bin\java.exe"
set JAR_FILE="spring-boot-backend/target/genetic-programming-0.0.1-SNAPSHOT.jar"

if not exist %JAVA_PATH% (
    echo [!] Aviso: No se encontro Java en la ruta especificada. Intentando usar 'java' del sistema...
    set JAVA_PATH=java
)

if not exist %JAR_FILE% (
    echo [X] Error: No se encuentra el archivo JAR en %JAR_FILE%
    echo [!] Asegurate de haber compilado el proyecto de Java primero.
    pause
    exit /b 1
)

echo [2/3] Iniciando Backend de Python (Port 8000)...
start "Python-Backend" /min python -m uvicorn main:aplicacion_servidor_web --port 8000

echo [3/3] Iniciando Frontend de Java (Port 8080)...
start "Java-Frontend" /min %JAVA_PATH% -jar %JAR_FILE%

echo.
echo ======================================================
echo Servidores en ejecucion en segundo plano.
echo API Python: http://localhost:8000
echo Interfaz Java: http://localhost:8080
echo ======================================================
echo.
pause
