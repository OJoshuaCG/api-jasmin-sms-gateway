from pydantic import BaseModel


class SmppConnectorStatsOut(BaseModel):
    cid: str
    # Timestamps — null when the event has never occurred
    created_at: str | None = None
    connected_at: str | None = None
    bound_at: str | None = None
    disconnected_at: str | None = None
    last_received_pdu_at: str | None = None
    last_sent_pdu_at: str | None = None
    # Counters
    connected_count: int = 0
    bound_count: int = 0
    disconnected_count: int = 0
    submit_sm_request_count: int = 0
    submit_sm_count: int = 0
    deliver_sm_count: int = 0
    elink_count: int = 0
    throttling_error_count: int = 0
    other_submit_error_count: int = 0
    interceptor_error_count: int = 0
    interceptor_count: int = 0


class SmppConnectorStatsSummary(BaseModel):
    """Row from stats --smppcs (one entry per connector)."""
    cid: str
    connected_at: str | None = None
    bound_at: str | None = None
    disconnected_at: str | None = None
    submits: str = "0/0"
    delivers: str = "0/0"
    qos_errors: int = 0
    other_errors: int = 0


class UserStatsOut(BaseModel):
    uid: str
    # SMPP Server counters
    smpp_bind_count: int = 0
    smpp_unbind_count: int = 0
    smpp_bound_connections: int = 0
    smpp_submit_sm_request_count: int = 0
    smpp_submit_sm_count: int = 0
    smpp_deliver_sm_count: int = 0
    smpp_elink_count: int = 0
    smpp_throttling_error_count: int = 0
    smpp_other_submit_error_count: int = 0
    smpp_last_activity_at: str | None = None
    # HTTP API counters
    http_connects_count: int = 0
    http_submit_sm_request_count: int = 0
    http_balance_request_count: int = 0
    http_rate_request_count: int = 0
    http_last_activity_at: str | None = None


class UserStatsSummary(BaseModel):
    """Row from stats --users (one entry per user)."""
    uid: str
    smpp_bound_connections: int = 0
    smpp_last_activity: str | None = None
    http_request_count: int = 0
    http_last_activity: str | None = None


class HttpApiStatsOut(BaseModel):
    created_at: str | None = None
    last_request_at: str | None = None
    last_success_at: str | None = None
    request_count: int = 0
    success_count: int = 0
    auth_error_count: int = 0
    route_error_count: int = 0
    interceptor_error_count: int = 0
    interceptor_count: int = 0
    throughput_error_count: int = 0
    charging_error_count: int = 0
    server_error_count: int = 0


class SmppServerApiStatsOut(BaseModel):
    created_at: str | None = None
    last_received_pdu_at: str | None = None
    last_sent_pdu_at: str | None = None
    connected_count: int = 0
    connect_count: int = 0
    disconnect_count: int = 0
    bound_trx_count: int = 0
    bound_rx_count: int = 0
    bound_tx_count: int = 0
    bind_trx_count: int = 0
    bind_rx_count: int = 0
    bind_tx_count: int = 0
    unbind_count: int = 0
    submit_sm_request_count: int = 0
    submit_sm_count: int = 0
    deliver_sm_count: int = 0
    elink_count: int = 0
    throttling_error_count: int = 0
    other_submit_error_count: int = 0
    interceptor_error_count: int = 0
    interceptor_count: int = 0


class GlobalStatsOut(BaseModel):
    smpp_connectors: list[SmppConnectorStatsSummary] = []
    users: list[UserStatsSummary] = []
    http_api: HttpApiStatsOut = HttpApiStatsOut()
    smpp_server_api: SmppServerApiStatsOut = SmppServerApiStatsOut()
