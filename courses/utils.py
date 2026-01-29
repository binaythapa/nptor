import re

def youtube_embed_url(url):
    """
    Converts YouTube URLs to SAFE embeddable format
    """
    if not url:
        return None

    patterns = [
        r"youtube\.com/watch\?v=([^&]+)",
        r"youtu\.be/([^?&]+)",
        r"youtube\.com/embed/([^?&]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            return (
                f"https://www.youtube-nocookie.com/embed/{video_id}"
                f"?rel=0&modestbranding=1"
            )

    return None
