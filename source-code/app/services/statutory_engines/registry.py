"""Registry and resolver for statutory payroll engines."""

from app.services.statutory_engines.base import (
    UnsupportedStatutoryEngineError,
)
from app.services.statutory_engines.zambia import (
    ZambiaStatutoryEngine,
)
from app.services.statutory_engines.zimbabwe import (
    ZimbabweStatutoryEngine,
)

from app.services.statutory_engines.botswana import (
    BotswanaStatutoryEngine,
)


class StatutoryEngineRegistryError(
    UnsupportedStatutoryEngineError
):
    """Raised when an engine identifier is unsupported."""


class StatutoryEngineRegistry:
    """Resolve rule-set engine identifiers to engine instances."""

    _registry = {}

    @classmethod
    def register(cls, engine_class):
        """Register one engine class under all supported keys."""

        keys = engine_class.supported_keys()

        if not keys:
            raise ValueError(
                "A statutory engine must define an engine_key."
            )

        for key in keys:
            existing = cls._registry.get(key)

            if (
                existing is not None
                and existing is not engine_class
            ):
                raise ValueError(
                    f"Statutory engine key {key!r} is already registered."
                )

            cls._registry[key] = engine_class

        return engine_class

    @staticmethod
    def normalize_key(value):
        """Normalize one engine identifier."""

        return str(value or "").strip().upper()

    @classmethod
    def resolve(cls, engine_key):
        """Return an initialized engine."""

        normalized_key = cls.normalize_key(
            engine_key
        )

        if not normalized_key:
            raise StatutoryEngineRegistryError(
                "A statutory engine identifier is required."
            )

        engine_class = cls._registry.get(
            normalized_key
        )

        if engine_class is None:
            supported = ", ".join(
                sorted(cls._registry)
            )

            raise StatutoryEngineRegistryError(
                (
                    f"Unsupported statutory engine "
                    f"{normalized_key!r}. "
                    f"Registered keys: {supported}."
                )
            )

        return engine_class()

    @classmethod
    def resolve_for_rule_set(cls, rule_set):
        """Resolve the configured engine for an operational rule set."""

        if rule_set is None:
            raise ValueError(
                "A statutory rule set is required."
            )

        engine_key = (
            getattr(
                rule_set,
                "source_engine_type",
                None,
            )
            or getattr(
                rule_set,
                "engine_type",
                None,
            )
        )

        if not engine_key:
            country_code = str(
                getattr(
                    rule_set,
                    "source_country_code",
                    "",
                )
                or ""
            ).strip().upper()

            currency = str(
                getattr(
                    rule_set,
                    "currency",
                    "",
                )
                or ""
            ).strip().upper()

            if (
                country_code == "ZM"
                or currency == "ZMW"
            ):
                engine_key = (
                    ZambiaStatutoryEngine.engine_key
                )
            elif (
                country_code == "ZW"
                or currency in {"USD", "ZWG"}
            ):
                engine_key = (
                    ZimbabweStatutoryEngine.engine_key
                )

        if not engine_key:
            raise StatutoryEngineRegistryError(
                (
                    "The operational statutory rule set "
                    "does not identify a supported engine."
                )
            )

        return cls.resolve(
            engine_key
        )

    @classmethod
    def validate_rule_set(
        cls,
        rule_set,
        statutory_config,
    ):
        """Validate one rule set against its resolved engine."""

        engine = cls.resolve_for_rule_set(
            rule_set
        )

        return engine.validate_configuration(
            statutory_config
        )

    @classmethod
    def registered_keys(cls):
        """Return every registered engine identifier."""

        return tuple(
            sorted(cls._registry)
        )


StatutoryEngineRegistry.register(
    ZimbabweStatutoryEngine
)

StatutoryEngineRegistry.register(
    ZambiaStatutoryEngine
)

StatutoryEngineRegistry.register(
    BotswanaStatutoryEngine
)
