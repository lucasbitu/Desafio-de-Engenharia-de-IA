"""Thin Streamlit interface for the frozen ticket-classification backend."""

from __future__ import annotations

import os
from pathlib import Path

import streamlit as st
from pydantic import ValidationError

from ticket_classifier.config import DEFAULT_DEVELOPMENT_MODEL_PATH
from ticket_classifier.delivery import DeliveryPredictionService
from ticket_classifier.llm_justification import rewriter_from_environment


MODEL_PATH = DEFAULT_DEVELOPMENT_MODEL_PATH


@st.cache_resource(show_spinner="Loading the classification model...")
def load_service(model_path: Path) -> DeliveryPredictionService:
    """Load the model once; all prediction behavior remains in the backend."""
    rewriter = None
    if os.environ.get("ENABLE_LLM_JUSTIFICATION", "").casefold() in {"1", "true", "yes"}:
        try:
            rewriter = rewriter_from_environment()
        except Exception:
            rewriter = None
    return DeliveryPredictionService.from_model_path(
        model_path,
        justification_rewriter=rewriter,
    )


def main() -> None:
    st.set_page_config(
        page_title="QuantumRise Ticket Classifier",
        page_icon="🎫",
        layout="centered",
    )
    st.title("QuantumRise Ticket Classifier")
    st.write(
        "Enter an IT service ticket to receive its predicted class and a short, "
        "evidence-based justification."
    )

    if not MODEL_PATH.is_file():
        st.error(
            "The development model is not available. Run `ticket-train` before "
            "starting the interface."
        )
        st.stop()

    try:
        service = load_service(MODEL_PATH)
    except Exception:
        st.error(
            "The classification model could not be loaded. Reproduce the development "
            "training and try again."
        )
        st.stop()

    ticket_text = st.text_area(
        "Ticket text",
        placeholder="Example: I cannot access my account after changing my password.",
        height=180,
    )
    show_diagnostics = st.checkbox("Show internal confidence diagnostics")

    if not st.button("Classify ticket", type="primary", use_container_width=True):
        return
    if not ticket_text.strip():
        st.warning("Enter a ticket before requesting a classification.")
        return

    try:
        prediction = service.predict(ticket_text)
        public_output = prediction.model_dump(by_alias=True)
    except ValidationError as error:
        st.error(f"Invalid ticket: {error.errors()[0]['msg']}")
        return
    except Exception:
        st.error("The ticket could not be classified. Please try again.")
        return

    st.subheader("Classification result")
    st.metric("Class", public_output["class"])
    st.write(public_output["justification"])
    st.markdown("#### Required JSON output")
    st.json(public_output)

    if show_diagnostics:
        diagnostics = service.diagnose(ticket_text)
        if diagnostics.low_confidence:
            st.warning(
                "Low-confidence prediction. The predicted class is preserved, but the "
                "ticket may benefit from human review."
            )
        else:
            st.success("The prediction is above the frozen low-confidence threshold.")
        st.caption(f"Estimated model confidence: {diagnostics.confidence:.3f}")


if __name__ == "__main__":
    main()
