try:
    from dependency_injector import containers, providers
except ModuleNotFoundError:  # pragma: no cover - fallback for minimal envs
    class containers:
        class DeclarativeContainer:
            pass

    class providers:
        class Configuration(dict):
            def override(self, value):
                self.update(value)

        class Singleton:
            def __init__(self, cls, *args, **kwargs):
                self.cls = cls
                self.args = args
                self.kwargs = kwargs
                self._instance = None

            def __call__(self):
                if self._instance is None:
                    self._instance = self.cls(*self.args, **self.kwargs)
                return self._instance

from ..config.settings import settings

class Container(containers.DeclarativeContainer):
    config = providers.Configuration()
    # Override configuration with loaded settings dictionary
    config.override(settings)

    # Example: Register components here
    # logger = providers.Singleton(YourLoggerClass)
    # wallet_manager = providers.Singleton(WalletManager, encryption_key=config.WALLET_ENCRYPTION_KEY)
