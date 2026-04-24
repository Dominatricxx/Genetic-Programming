package com.uabc.gp.controller;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.HttpStatusCodeException;
import org.springframework.web.client.RestTemplate;

import java.util.Map;

@RestController
@RequestMapping("/api")
public class ExperimentoController {

    private static final Logger log = LoggerFactory.getLogger(ExperimentoController.class);

    @Autowired
    private RestTemplate puenteDePeticionesInternas;

    // El microservicio de Python corre en el puerto 8000
    private final String DIRECCION_DEL_MICROSERVICIO_PYTHON = "http://127.0.0.1:8000/api/experimento";

    @PostMapping("/experimento")
    public ResponseEntity<?> correrAlgoritmoEvolutivo(@RequestBody Map<String, Object> datosRecibidosDelUsuario) {
        log.info("Recibida petición para experimento: {}", datosRecibidosDelUsuario.get("dataset"));
        try {
            ResponseEntity<String> respuestaCalculadaPorPython = puenteDePeticionesInternas.postForEntity(
                    DIRECCION_DEL_MICROSERVICIO_PYTHON,
                    datosRecibidosDelUsuario,
                    String.class
            );
            
            log.info("Petición procesada exitosamente por Python");
            return ResponseEntity.status(respuestaCalculadaPorPython.getStatusCode()).body(respuestaCalculadaPorPython.getBody());
        } catch (HttpStatusCodeException e) {
            log.error("Error devuelto por el microservicio de Python: {} - {}", e.getStatusCode(), e.getResponseBodyAsString());
            return ResponseEntity.status(e.getStatusCode()).body(e.getResponseBodyAsString());
        } catch (Exception excepcionCapturada) {
            log.error("Error crítico al comunicarse con Python: {}", excepcionCapturada.getMessage(), excepcionCapturada);
            return ResponseEntity.status(500)
                .body(Map.of("detail", "Error de conexión con el motor de IA en Python: " + excepcionCapturada.getMessage()));
        }
    }
}
