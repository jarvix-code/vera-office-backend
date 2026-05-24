"""
List all registered FastAPI routes
"""
from backend.main import app

def list_routes():
    """Print all routes."""
    print("Registered routes:\n")
    for route in app.routes:
        if hasattr(route, 'methods'):
            methods = ', '.join(route.methods)
            print(f"{methods:10} {route.path}")
        else:
            print(f"{'':10} {route.path}")

if __name__ == "__main__":
    list_routes()
