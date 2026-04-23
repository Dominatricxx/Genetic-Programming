package com.uabc.gp.controller;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestTemplate;

import java.util.Map;

@RestController
@RequestMapping("/api")
public class ExperimentoController {

    @Autowired
    private RestTemplate puenteDePeticionesInternas;

    // El microservicio de Python corre en el puerto 8000
    private final String DIRECCION_DEL_MICROSERVICIO_PYTHON = "http://127.0.0.1:8000/api/experimento";

    @PostMapping("/experimento")
    public ResponseEntity<?> correrAlgoritmoEvolutivo(@RequestBody Map<String, Object> datosRecibidosDelUsuario) {
        try {
            // Reenviar la petición matemática al microservicio de Python
            ResponseEntity<String> respuestaCalculadaPorPython = puenteDePeticionesInternas.postForEntity(
                    DIRECCION_DEL_MICROSERVICIO_PYTHON,
                    datosRecibidosDelUsuario,
                    String.class
            );
            
            // Devolver al frontend los resultados exactos que Python generó
            return ResponseEntity.status(respuestaCalculadaPorPython.getStatusCode()).body(respuestaCalculadaPorPython.getBody());
        } catch (Exception excepcionCapturada) {
            return ResponseEntity.status(500)
                .body(Map.of("detail", "Error crítico al comunicarse con el motor de Inteligencia Artificial en Python: " + excepcionCapturada.getMessage()));
        }
    }
}
