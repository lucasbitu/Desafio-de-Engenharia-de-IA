"""Backward-compatible name for the consolidated delivery service."""

from .delivery import DeliveryPredictionService

TicketPredictionService = DeliveryPredictionService

__all__ = ["TicketPredictionService"]
