"""Deal / negotiation state machine (CLAUDE.md s.5).

INQUIRY -> CHAT_OPEN(after tenant CNIC+OTP) -> OFFER_SENT -> (COUNTERED <-> OFFER_SENT)
        -> ACCEPTED -> AGREEMENT_GENERATED -> SIGNED_OFFLINE

M6 implements INQUIRY -> CHAT_OPEN and the messaging that rides on CHAT_OPEN. The offer
states (OFFER_SENT/COUNTERED/ACCEPTED) are wired in M7, the agreement states in M8. The full
map is encoded here so later milestones just use it. Pure — unit-testable on its own.
"""
from __future__ import annotations

from enum import Enum


class DealStatus(str, Enum):
    INQUIRY = "INQUIRY"
    CHAT_OPEN = "CHAT_OPEN"
    OFFER_SENT = "OFFER_SENT"
    COUNTERED = "COUNTERED"
    ACCEPTED = "ACCEPTED"
    AGREEMENT_GENERATED = "AGREEMENT_GENERATED"
    SIGNED_OFFLINE = "SIGNED_OFFLINE"


_ALLOWED: dict[DealStatus, set[DealStatus]] = {
    DealStatus.INQUIRY: {DealStatus.CHAT_OPEN},
    DealStatus.CHAT_OPEN: {DealStatus.OFFER_SENT},
    DealStatus.OFFER_SENT: {DealStatus.COUNTERED, DealStatus.ACCEPTED},
    DealStatus.COUNTERED: {DealStatus.OFFER_SENT, DealStatus.ACCEPTED},
    DealStatus.ACCEPTED: {DealStatus.AGREEMENT_GENERATED},
    DealStatus.AGREEMENT_GENERATED: {DealStatus.SIGNED_OFFLINE},
    DealStatus.SIGNED_OFFLINE: set(),
}


def can_transition(current: DealStatus, target: DealStatus) -> bool:
    return target in _ALLOWED.get(current, set())


class MessageType(str, Enum):
    TEXT = "text"
    OFFER = "offer"     # structured offers arrive in M7
    SYSTEM = "system"   # platform-generated notices


# States in which a deal accepts (counter-)offers.
NEGOTIABLE = {DealStatus.CHAT_OPEN, DealStatus.OFFER_SENT, DealStatus.COUNTERED}


class OfferStatus(str, Enum):
    PENDING = "PENDING"        # the offer currently on the table
    SUPERSEDED = "SUPERSEDED"  # replaced by a later counter-offer
    ACCEPTED = "ACCEPTED"      # accepted by the counter-party; deal terms locked
