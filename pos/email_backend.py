"""
Backend personalizado de email para evitar problemas con starttls()
"""
import smtplib
from django.core.mail.backends.smtp import EmailBackend as SMTPEmailBackend


class CustomSMTPEmailBackend(SMTPEmailBackend):
    """
    Backend SMTP personalizado que evita el problema con starttls() y keyfile
    """
    
    def open(self):
        """
        Abre una conexión SMTP y la autentica.
        Sobrescribe el método para evitar el problema con keyfile en starttls()
        """
        if self.connection:
            return False
        
        try:
            # Si se usa SSL, crear conexión SSL directamente
            if self.use_ssl:
                self.connection = smtplib.SMTP_SSL(
                    self.host,
                    self.port,
                    timeout=self.timeout
                )
            else:
                # Si se usa TLS, crear conexión normal y luego iniciar TLS
                self.connection = smtplib.SMTP(
                    self.host,
                    self.port,
                    timeout=self.timeout
                )
                if self.use_tls:
                    # Llamar a starttls() sin argumentos adicionales
                    self.connection.starttls()
            
            # Autenticar si es necesario
            if self.username and self.password:
                self.connection.login(self.username, self.password)
            
            return True
        except Exception:
            if not self.fail_silently:
                raise

