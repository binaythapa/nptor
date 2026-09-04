/* Course video progress tracker.
 * Uses the YouTube IFrame API so progress reflects the actual player time
 * instead of an elapsed-page timer.
 */
(function () {
    "use strict";

    const iframe = document.getElementById("courseVideoPlayer");
    if (!iframe) return;

    const endpoint = iframe.dataset.progressUrl;
    const lessonId = iframe.dataset.lessonId;
    const status = document.getElementById("video-status");
    let player;
    let completed = false;
    let lastSent = 0;
    let progressTimer;

    function getCookie(name) {
        const prefix = name + "=";
        for (const cookie of document.cookie.split(";")) {
            const value = cookie.trim();
            if (value.startsWith(prefix)) {
                return decodeURIComponent(value.slice(prefix.length));
            }
        }
        return "";
    }

    function sendProgress() {
        if (!player || typeof player.getCurrentTime !== "function") return;

        const watched = Math.max(0, Math.floor(player.getCurrentTime()));
        const duration = Math.max(0, Math.floor(player.getDuration()));

        if (!duration || watched < lastSent) return;
        if (watched - lastSent < 5 && watched < duration * 0.9) return;

        lastSent = watched;

        fetch(endpoint, {
            method: "POST",
            headers: {
                "X-CSRFToken": getCookie("csrftoken"),
                "Content-Type": "application/x-www-form-urlencoded",
                "X-Requested-With": "XMLHttpRequest"
            },
            body: new URLSearchParams({
                lesson_id: lessonId,
                watched: String(watched),
                duration: String(duration)
            })
        })
            .then(function (response) {
                if (!response.ok) throw new Error("Video progress request failed");
                return response.json();
            })
            .then(function (data) {
                if (data.completed && !completed) {
                    completed = true;
                    if (status) status.textContent = "✔ Video watched. Lesson completed";
                    if (progressTimer) {
                        window.clearInterval(progressTimer);
                        progressTimer = null;
                    }
                }
            })
            .catch(function (error) {
                console.error("Video tracking error:", error);
            });
    }

    function onReady(event) {
        player = event.target;
        if (progressTimer) window.clearInterval(progressTimer);
        progressTimer = window.setInterval(function () {
            if (player && player.getPlayerState() === YT.PlayerState.PLAYING) {
                sendProgress();
            }
        }, 5000);
    }

    function onStateChange(event) {
        if (event.data === YT.PlayerState.ENDED) {
            sendProgress();
        }
    }

    function initializePlayer() {
        if (!window.YT || !window.YT.Player) return;
        new YT.Player("courseVideoPlayer", {
            events: {
                onReady: onReady,
                onStateChange: onStateChange
            }
        });
    }

    function loadApi() {
        if (window.YT && window.YT.Player) {
            initializePlayer();
            return;
        }

        const previous = window.onYouTubeIframeAPIReady;
        window.onYouTubeIframeAPIReady = function () {
            if (typeof previous === "function") previous();
            initializePlayer();
        };

        if (!document.querySelector('script[src="https://www.youtube.com/iframe_api"]')) {
            const script = document.createElement("script");
            script.src = "https://www.youtube.com/iframe_api";
            document.head.appendChild(script);
        }
    }

    loadApi();
})();
