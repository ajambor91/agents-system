class HealthCheck:
  
    def check_status(self):
        return {"status": "healthy"}

    def is_healthy(self):
        return True