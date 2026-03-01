from urllib.parse import quote


class ShareService:

    @staticmethod
    def generate_achievement_text(
        title,
        readiness=None,
        predicted_score=None,
        rank=None,
        url="https://nptor.com"
    ):
        parts = [f"I just completed {title} on nptor.com! 🎉"]

        if readiness is not None:
            parts.append(f"🎯 Readiness: {readiness}%")

        if predicted_score is not None:
            parts.append(f"📊 Predicted Score: {predicted_score}%")

        if rank is not None:
            parts.append(f"🏆 Global Rank: #{rank}")

        parts.append("🚀 Prepare smarter. Compete globally.")
        parts.append(url)

        return "\n".join(parts)

    @staticmethod
    def get_social_links(text, url="https://nptor.com"):

        encoded_text = quote(text)
        encoded_url = quote(url)

        return {
            # LinkedIn shares URL (text must be on landing page meta tags)
            "linkedin": (
                f"https://www.linkedin.com/sharing/share-offsite/"
                f"?url={encoded_url}"
            ),

            # Facebook shares URL
            "facebook": (
                f"https://www.facebook.com/sharer/sharer.php"
                f"?u={encoded_url}"
            ),

            # Twitter allows both text + URL
            "twitter": (
                f"https://twitter.com/intent/tweet"
                f"?text={encoded_text}"
                f"&url={encoded_url}"
            ),
        }