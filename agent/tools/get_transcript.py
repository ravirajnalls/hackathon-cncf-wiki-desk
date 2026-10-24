"""Pull YouTube captions with timestamps into SQLite chunks."""

from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

from agent.db import get_db, video_ingested, record_video


def extract_video_id(url: str) -> str | None:
    """Extract YouTube video ID from various URL formats."""
    if "youtube.com/watch" in url:
        from urllib.parse import urlparse, parse_qs
        qs = parse_qs(urlparse(url).query)
        return qs.get("v", [None])[0]
    if "youtu.be/" in url:
        return url.split("youtu.be/")[-1].split("?")[0]
    if "youtube.com/embed/" in url:
        return url.split("youtube.com/embed/")[-1].split("?")[0]
    return None


def get_transcript(video_url: str, metadata: dict | None = None) -> dict:
    """Fetch captions with timestamps for a YouTube video.

    Returns: {video_id, chunks_ingested, title, speaker, year, error?}
    """
    video_id = extract_video_id(video_url)
    if not video_id:
        return {"error": f"Could not parse video ID from {video_url}"}

    if video_ingested(video_id):
        return {"video_id": video_id, "chunks_ingested": 0, "status": "already_ingested"}

    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=["en"])
    except (TranscriptsDisabled, NoTranscriptFound) as e:
        return {"video_id": video_id, "error": str(e)}
    except Exception as e:
        return {"video_id": video_id, "error": str(e)}

    # Merge short captions into ~60s chunks for better FTS search
    chunks = []
    current_text = ""
    current_start = 0.0
    current_end = 0.0

    for entry in transcript:
        if not current_text:
            current_start = entry["start"]
        current_text += " " + entry["text"]
        current_end = entry["start"] + entry.get("duration", 0)

        if current_end - current_start >= 45:  # ~45s chunks
            chunks.append({
                "video_id": video_id,
                "t_start": int(current_start),
                "t_end": int(current_end),
                "text": current_text.strip(),
            })
            current_text = ""

    # Don't forget the last chunk
    if current_text:
        chunks.append({
            "video_id": video_id,
            "t_start": int(current_start),
            "t_end": int(current_end),
            "text": current_text.strip(),
        })

    # Store in DB
    with get_db() as conn:
        conn.executemany(
            "INSERT INTO chunks (video_id, t_start, t_end, text) VALUES (:video_id, :t_start, :t_end, :text)",
            chunks,
        )

    meta = metadata or {}
    record_video(
        video_id,
        title=meta.get("title", ""),
        speaker=meta.get("author", ""),
        year=meta.get("year", ""),
    )

    return {
        "video_id": video_id,
        "chunks_ingested": len(chunks),
        "status": "ingested",
    }


def format_timestamp_link(video_id: str, t_seconds: int) -> str:
    """Format a clickable YouTube timestamp link."""
    mins, secs = divmod(t_seconds, 60)
    return f"[▶ {mins}:{secs:02d}](https://youtube.com/watch?v={video_id}&t={t_seconds}s)"
