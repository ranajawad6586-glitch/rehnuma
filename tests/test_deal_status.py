"""Deal state-machine transitions — pure, runs anywhere with just pytest."""
from app.deals.status import DealStatus as D
from app.deals.status import MessageType, can_transition


def test_chat_opens_only_from_inquiry():
    assert can_transition(D.INQUIRY, D.CHAT_OPEN)
    assert not can_transition(D.INQUIRY, D.OFFER_SENT)


def test_offer_counter_loop():
    assert can_transition(D.CHAT_OPEN, D.OFFER_SENT)
    assert can_transition(D.OFFER_SENT, D.COUNTERED)
    assert can_transition(D.COUNTERED, D.OFFER_SENT)
    assert can_transition(D.OFFER_SENT, D.ACCEPTED)


def test_full_forward_chain_to_signed():
    assert can_transition(D.ACCEPTED, D.AGREEMENT_GENERATED)
    assert can_transition(D.AGREEMENT_GENERATED, D.SIGNED_OFFLINE)
    assert not can_transition(D.SIGNED_OFFLINE, D.OFFER_SENT)


def test_cannot_skip_chat():
    # No messaging path without first opening chat (tenant verification gate).
    assert not can_transition(D.INQUIRY, D.ACCEPTED)


def test_message_types():
    assert {t.value for t in MessageType} == {"text", "offer", "system"}
