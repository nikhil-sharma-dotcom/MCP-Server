from locust import HttpUser, task, between

class MCPUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task
    def check_validation(self):
        # Simulates a high-frequency call to your compliance logic
        self.client.get("/validate") 

    @task
    def check_high_value(self):
        self.client.post("/high-value", json={"min_amount": 1000})