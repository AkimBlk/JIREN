from django.db import models
from django.core.exceptions import ValidationError

class StoryPointsScheme(models.Model):
    FIBONACCI = "fibonacci"
    POWERS_2 = "powers_2"
    LINEAR = "linear"
    
    SCHEMES = {
        FIBONACCI: [1, 2, 3, 5, 8, 13, 21, 34, 55, 89],
        POWERS_2: [1, 2, 4, 8, 16, 32],
        LINEAR: list(range(1, 11)),
    }
    
    project = models.OneToOneField("Project", on_delete=models.CASCADE, related_name="story_points_scheme")
    scheme_type = models.CharField(max_length=20, choices=[(k, k) for k in SCHEMES], default=FIBONACCI)
    
    def get_allowed_values(self):
        return self.SCHEMES.get(self.scheme_type, [])
    
    def is_valid(self, value):
        return value in self.get_allowed_values()
    
    def __str__(self):
        return f"{self.project.name} - {self.scheme_type}"
