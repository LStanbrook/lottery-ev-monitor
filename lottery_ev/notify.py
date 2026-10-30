import subprocess
import urllib.request

# Toasts are sent as PowerShell, which Windows already trusts to show notifications.
_PS_APP_ID = r"{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe"


def _ps_quote(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def windows_toast(title: str, body: str) -> None:
    script = f"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
$xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$text = $xml.GetElementsByTagName('text')
$text.Item(0).AppendChild($xml.CreateTextNode({_ps_quote(title)})) > $null
$text.Item(1).AppendChild($xml.CreateTextNode({_ps_quote(body)})) > $null
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier({_ps_quote(_PS_APP_ID)}).Show([Windows.UI.Notifications.ToastNotification]::new($xml))
"""
    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                   check=False, capture_output=True)


def ntfy(topic: str, title: str, body: str) -> None:
    """Push to your phone via ntfy.sh (install the ntfy app and subscribe to the same topic)."""
    req = urllib.request.Request(f"https://ntfy.sh/{topic}", data=body.encode("utf-8"),
                                 headers={"Title": title.encode("utf-8")}, method="POST")
    urllib.request.urlopen(req, timeout=15).close()
