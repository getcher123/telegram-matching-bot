"""Pydantic models for YAML configuration."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class StorageDriver(StrEnum):
    sqlite = "sqlite"
    postgresql = "postgresql"


class AlertTarget(BaseModel):
    title: str
    peer: str
    enabled: bool = True


class AlertMessageConfig(BaseModel):
    include_original_text: bool = True
    include_normalized_excerpt: bool = True
    include_evidence: bool = True
    include_forwarded_message_when_link_unavailable: bool = True
    max_original_text_chars: int = 900


class MonitoredChat(BaseModel):
    title: str
    peer: str = ""
    peer_id: int | None = None
    enabled: bool = True


class TelegramConfig(BaseModel):
    session_file: str = "./var/telegram/session.marketwatch"
    api_id_env: str = "TG_API_ID"
    api_hash_env: str = "TG_API_HASH"
    phone_env: str = "TG_PHONE"
    connect_timeout_seconds: int = 20
    request_timeout_seconds: int = 30
    sequential_updates: bool = True
    process_new_messages: bool = True
    process_edited_messages: bool = True
    ignore_outgoing_messages: bool = True
    monitored_chats: list[MonitoredChat] = Field(default_factory=list)
    alert_targets: list[AlertTarget] = Field(default_factory=list)
    alert_message: AlertMessageConfig = Field(default_factory=AlertMessageConfig)


class CatchUpConfig(BaseModel):
    enabled: bool = True
    interval_seconds: int = 120
    messages_per_chat_limit: int = 80


class NormalizationConfig(BaseModel):
    unicode_nfkc: bool = True
    lowercase: bool = True
    replace_yo_with_e: bool = True
    remove_zero_width_chars: bool = True
    normalize_quotes: bool = True
    normalize_dashes: bool = True
    normalize_currency: bool = True
    fix_mixed_cyrillic_latin_for_known_terms: bool = True
    fix_keyboard_layout_for_known_terms: bool = True
    transliterate_known_product_terms: bool = True
    collapse_repeated_spaces: bool = True
    max_edit_distance_for_dictionary_terms: int = 1
    use_edit_distance_only_for_terms_min_length: int = 5
    token_window_for_context: int = 8


class EngineConfig(BaseModel):
    deterministic: bool = True
    default_rule_threshold: int = 100
    global_reject_if_any_intent: list[str] = Field(
        default_factory=lambda: ["buy", "repair", "review", "rent", "wanted"]
    )
    deduplicate_alerts: bool = True
    duplicate_text_fingerprint_window_hours: int = 24
    alert_rate_limit_per_minute: int = 20
    dry_run: bool = False


class StorageConfig(BaseModel):
    driver: StorageDriver = StorageDriver.sqlite
    sqlite_path: str = "./var/db/tg_market_watch.sqlite3"
    retention_days_messages: int = 30
    retention_days_matches: int = 180
    store_full_text: bool = True
    store_sender_id: bool = True


class NumericConstraint(BaseModel):
    entity: str
    operator: str  # >=, <=, ==, range
    value: float
    required: bool = True
    context_dictionary_any: list[str] | None = None
    context_window_tokens: int | None = None

    @field_validator("operator")
    @classmethod
    def validate_operator(cls, v: str) -> str:
        allowed = {">=", "<=", "==", "range", ">", "<"}
        if v not in allowed:
            raise ValueError(f"Operator must be one of: {', '.join(sorted(allowed))}")
        return v


class RuleConfig(BaseModel):
    id: str
    title: str
    enabled: bool = True
    priority: str = "medium"  # low, medium, high
    threshold: int = 100
    require_intent_any: list[str] | None = None
    reject_intent_any: list[str] | None = None
    require_dictionary_any: list[str] | None = None
    require_dictionary_all: list[str] | None = None
    reject_dictionary_any: list[str] | None = None
    numeric_constraints: list[NumericConstraint] | None = None
    evidence_weights: dict[str, int] | None = None
    alert_template_id: str = "default_market_match"


class DictionaryGroup(BaseModel):
    canonical: str
    terms: list[str]


class AppConfig(BaseModel):
    name: str = "tg-market-watch"
    environment: str = "local"
    timezone: str = "Asia/Tbilisi"
    admin_api_token_env: str = "ADMIN_API_TOKEN"
    data_dir: str = "./var"
    log_level: str = "INFO"


class RootConfig(BaseModel):
    version: int = 1
    app: AppConfig = Field(default_factory=AppConfig)
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    catch_up: CatchUpConfig = Field(default_factory=CatchUpConfig)
    normalization: NormalizationConfig = Field(default_factory=NormalizationConfig)
    engine: EngineConfig = Field(default_factory=EngineConfig)
    dictionaries: dict[str, list[DictionaryGroup]] = Field(default_factory=dict)
    rules: list[RuleConfig] = Field(default_factory=list)
