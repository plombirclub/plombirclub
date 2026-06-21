import enum


class UserRole(str, enum.Enum):
    user = "user"
    admin = "admin"


class PointsLedgerStatus(str, enum.Enum):
    pending = "pending"
    active = "active"
    inactive = "inactive"
    redeemed = "redeemed"
    pending_redemption = "pending_redemption"


class PrizeType(str, enum.Enum):
    certificate = "certificate"
    money = "money"


class PointsOperationType(str, enum.Enum):
    import_ = "import"
    activation = "activation"
    reserve = "reserve"
    refund = "refund"
    redeem = "redeem"
    manual_adjustment = "manual_adjustment"


class RequestStatus(str, enum.Enum):
    verification_pending = "verification_pending"
    placed = "placed"
    confirmed = "confirmed"
    rejected = "rejected"
    processing = "processing"
    fulfilled = "fulfilled"
    cancelled = "cancelled"


class VerificationMethod(str, enum.Enum):
    sms = "sms"
    email = "email"


class VerificationTargetType(str, enum.Enum):
    profile_phone = "profile_phone"
    request_payout_phone = "request_payout_phone"
    other = "other"


class MaterialContentType(str, enum.Enum):
    pdf = "pdf"
    pptx = "pptx"
    video = "video"
    image = "image"
    text = "text"


class MaterialProgressStatus(str, enum.Enum):
    not_started = "not_started"
    started = "started"
    completed = "completed"


class TaskType(str, enum.Enum):
    participation_conditions = "participation_conditions"
    points_activation = "points_activation"


class TaskSource(str, enum.Enum):
    system = "system"
    admin = "admin"


class ProductSource(str, enum.Enum):
    parser = "parser"
    manual = "manual"


class SystemLogLevel(str, enum.Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


class ImportType(str, enum.Enum):
    users = "users"
    sales = "sales"
