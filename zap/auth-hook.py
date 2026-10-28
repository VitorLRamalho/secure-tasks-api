import os


def zap_started(zap, target):
    """Chamado pelo zap-api-scan.py assim que o ZAP sobe: injeta o header Authorization."""
    zap.replacer.add_rule(
        description="jwt-auth",
        enabled="true",
        matchtype="REQ_HEADER",
        matchregex="false",
        matchstring="Authorization",
        replacement=f"Bearer {os.environ['ZAP_TOKEN']}",
    )
