/*!
 * Start Bootstrap - Grayscale v7.0.5 (https://startbootstrap.com/theme/grayscale)
 * Copyright 2013-2022 Start Bootstrap
 * Licensed under MIT (https://github.com/StartBootstrap/startbootstrap-grayscale/blob/master/LICENSE)
 */
//
// Scripts
// 
/*vericar si conecto a js*/
console.log('Conectado a script');

//INICIO DE SESION
$(document).ready(function() {
    // Primero, eliminamos cualquier evento submit previo registrado
    $('#login-form').off('submit').on('submit', function(e) {
        e.preventDefault();

        $.ajax({
            type: 'POST',
            url: $(this).attr('action'),
            data: $(this).serialize(),
            success: function(response) {
                if (response === 'error') {
                    console.log("error");
                    // Alerta por si el correo y contraseña están mal
                    $('#alertContainer').html('<div class="alert alert-danger">Verifica tu correo o contraseña.</div>');
                } else if (response === 'success') {
                    console.log("login");
                    window.location.href = '/inicio_principal';
                }
            },
            error: function() {
                // Error en la solicitud AJAX
                $('#alertContainer').html('<div class="alert alert-danger">Error en la solicitud.</div>');
            }
        });
    });
});


//REGISTRO DE CUENTA
$(document).ready(function() {
    // Primero, eliminamos cualquier evento submit previo registrado
    $('#registro-form').off('submit').on('submit', function(event) {
        // Evita el envío del formulario predeterminado
        event.preventDefault();

        // Verifica si el formulario HTML es válido
        if (this.checkValidity()) {
            // Obtiene la respuesta del hCaptcha
            var response = hcaptcha.getResponse();

            // Verifica si se proporcionó una respuesta válida
            if (response && response.trim() !== '') {
                // Envía el formulario a través de AJAX
                $.ajax({
                    type: 'POST',
                    url: $(this).attr('action'),
                    data: $(this).serialize(),
                    success: function(response) {
                        if (response === 'success') {
                            // Éxito: muestra un mensaje de éxito
                            $('#alertContainer').html('<div class="alert alert-success">Se ha creado la cuenta de manera exitosa.</div>');
                        } else if (response === 'exist') {
                            // Los datos ya existen: muestra una alerta
                            $('#alertContainer').html('<div class="alert alert-danger">Los datos ya existen.</div>');
                        }
                    },
                    error: function() {
                        // Error en la solicitud AJAX
                        $('#alertContainer').html('<div class="alert alert-danger">Error en la solicitud.</div>');
                    }
                });
            } else {
                // Si no se proporcionó una respuesta válida, muestra un mensaje de error
                $('#capContainer').html('<div class="alert alert-danger mt-3">Por favor completa el hCaptcha.</div>');
                setTimeout(function() {
                    document.getElementById("capContainer").style.display = "none";
                }, 2000); // 2000 milisegundos (2 segundos)
            }
        } else {
            // Si el formulario no es válido, permite que el navegador muestre los mensajes de error HTML5
            this.reportValidity();
        }
    });
});

//TOOLTIP

document.addEventListener('DOMContentLoaded', function() {
    const exampleEl = document.getElementById('busar_G');
    const tooltip = new bootstrap.Tooltip(exampleEl);
}); 

document.addEventListener('DOMContentLoaded', function() {
    const exampleEl = document.getElementById('file-button');
    const tooltip = new bootstrap.Tooltip(exampleEl);
}); 

document.addEventListener('DOMContentLoaded', function() {
    const exampleEl = document.getElementById('agregar-costo');
    const tooltip = new bootstrap.Tooltip(exampleEl);
}); 
document.addEventListener('DOMContentLoaded', function() {
    const exampleEl = document.getElementById('datos_actuales');
    const tooltip = new bootstrap.Tooltip(exampleEl);
}); 