class ValidatorRegistry:
    def __init__(self):
        self._validators = {}

    def register(self, validator):
        self._validators[validator.key] = validator

    def get(self, key):
        return self._validators.get(key)


registry = ValidatorRegistry()
