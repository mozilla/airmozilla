class GeneralException(Exception): pass


class ConfigurationException(Exception): pass


class UninitializedValueError(GeneralException): pass


class ConfigurationFileNotFound(ConfigurationException): pass


class ConfigurationFileInitialized(ConfigurationException): pass
