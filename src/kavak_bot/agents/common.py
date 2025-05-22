

def transfer_back_to_triage():
    """Call this if the user brings up a topic outside of your purview,
    including escalating to human."""
    from agents.triage_agent import triage_agent
    
    return triage_agent