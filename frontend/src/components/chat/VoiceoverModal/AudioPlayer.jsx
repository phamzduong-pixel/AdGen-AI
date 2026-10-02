import React, { useState, useRef, useEffect } from "react";
import {
  FiPlay,
  FiPause,
  FiDownload,
  FiVolume2,
  FiVolumeX,
  FiRotateCcw,
  FiLoader,
} from "react-icons/fi";
import "./VoiceoverModal.css";

export default function AudioPlayer({
  src,
  voiceName = "Voiceover",
  duration = 0,
  downloadUrl = null,
  compact = false,
}) {
  const audioRef = useRef(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [totalDuration, setTotalDuration] = useState(duration || 0);
  const [isMuted, setIsMuted] = useState(false);
  const [playbackRate, setPlaybackRate] = useState(1.0);
  const [isDownloading, setIsDownloading] = useState(false);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    setIsPlaying(false);
    setCurrentTime(0);
    if (duration) {
      setTotalDuration(duration);
    }

    const handlePlay = () => setIsPlaying(true);
    const handlePause = () => setIsPlaying(false);
    const handleTimeUpdate = () => setCurrentTime(audio.currentTime);
    const handleLoadedMetadata = () => {
      if (audio.duration && !isNaN(audio.duration) && audio.duration !== Infinity) {
        setTotalDuration(audio.duration);
      }
    };
    const handleEnded = () => {
      setIsPlaying(false);
      setCurrentTime(0);
    };
    const handleError = (e) => {
      console.warn("Audio element error on src:", src, e);
      setIsPlaying(false);
    };

    audio.addEventListener("play", handlePlay);
    audio.addEventListener("pause", handlePause);
    audio.addEventListener("timeupdate", handleTimeUpdate);
    audio.addEventListener("loadedmetadata", handleLoadedMetadata);
    audio.addEventListener("ended", handleEnded);
    audio.addEventListener("error", handleError);

    try {
      audio.load();
    } catch {
      // Ignore abort errors on reload
    }

    return () => {
      audio.removeEventListener("play", handlePlay);
      audio.removeEventListener("pause", handlePause);
      audio.removeEventListener("timeupdate", handleTimeUpdate);
      audio.removeEventListener("loadedmetadata", handleLoadedMetadata);
      audio.removeEventListener("ended", handleEnded);
      audio.removeEventListener("error", handleError);
    };
  }, [src, duration]);

  const togglePlay = () => {
    const audio = audioRef.current;
    if (!audio) return;

    if (audio.ended) {
      audio.currentTime = 0;
    }

    if (audio.paused) {
      audio.play().catch((e) => {
        console.error("Audio playback error:", e);
      });
    } else {
      audio.pause();
    }
  };

  const handleSeek = (e) => {
    const time = Number(e.target.value);
    setCurrentTime(time);
    if (audioRef.current) {
      audioRef.current.currentTime = time;
    }
  };

  const toggleMute = () => {
    if (!audioRef.current) return;
    audioRef.current.muted = !isMuted;
    setIsMuted(!isMuted);
  };

  const handleReset = () => {
    if (!audioRef.current) return;
    audioRef.current.currentTime = 0;
    setCurrentTime(0);
  };

  const cyclePlaybackRate = () => {
    const rates = [1.0, 1.25, 1.5, 0.8];
    const nextIdx = (rates.indexOf(playbackRate) + 1) % rates.length;
    const nextRate = rates[nextIdx];
    setPlaybackRate(nextRate);
    if (audioRef.current) {
      audioRef.current.playbackRate = nextRate;
    }
  };

  const handleDirectDownload = (e) => {
    e.preventDefault();
    const targetUrl = downloadUrl || (src ? `${src}?download=true` : null);
    if (!targetUrl) return;

    try {
      const link = document.createElement("a");
      link.href = targetUrl;
      const filename = targetUrl.split("/").pop().split("?")[0] || "voiceover.mp3";
      link.setAttribute("download", filename);
      link.setAttribute("target", "_blank");
      link.setAttribute("rel", "noopener noreferrer");
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err) {
      console.error("Download audio error:", err);
      window.open(targetUrl, "_blank");
    }
  };

  const formatTime = (secs) => {
    if (secs == null || isNaN(secs) || secs < 0) return "0:00";
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m}:${s < 10 ? "0" : ""}${s}`;
  };

  const rawPercent = totalDuration > 0 ? (currentTime / totalDuration) * 100 : 0;
  const progressPercent = Math.min(Math.max(isNaN(rawPercent) ? 0 : rawPercent, 0), 100);
  const displayVoice = voiceName || "Voiceover";

  if (!src) return null;

  return (
    <div className={`adgen-audio-player ${compact ? "adgen-audio-player--compact" : ""}`}>
      <audio ref={audioRef} src={src} preload="metadata" />

      <div className="adgen-audio-player__main">
        <button
          type="button"
          className="adgen-audio-btn adgen-audio-btn--play"
          onClick={togglePlay}
          title={isPlaying ? "Tạm dừng" : "Phát"}
          aria-label={isPlaying ? "Tạm dừng" : "Phát"}
        >
          {isPlaying ? <FiPause /> : <FiPlay />}
        </button>

        <div className="adgen-audio-player__content">
          <div className="adgen-audio-player__header">
            <span className="adgen-audio-player__badge">🎙️ Voiceover</span>
            <span className="adgen-audio-player__voice" title={displayVoice}>
              {displayVoice}
            </span>
          </div>

          <div className="adgen-audio-player__progress-wrap">
            <input
              type="range"
              min="0"
              max={totalDuration || 1}
              step="0.1"
              value={currentTime}
              onChange={handleSeek}
              className="adgen-audio-player__seekbar"
              style={{
                background: `linear-gradient(to right, var(--color-primary-500, #3b82f6) ${progressPercent}%, var(--color-gray-700, #374151) ${progressPercent}%)`,
              }}
            />
            <div className="adgen-audio-player__time">
              <span>{formatTime(currentTime)}</span>
              <span>/</span>
              <span>{formatTime(totalDuration)}</span>
            </div>
          </div>
        </div>

        <div className="adgen-audio-player__actions">
          <button
            type="button"
            className="adgen-audio-btn adgen-audio-btn--icon"
            onClick={cyclePlaybackRate}
            title={`Tốc độ phát (${playbackRate}x)`}
          >
            <span className="adgen-audio-speed-tag">{playbackRate}x</span>
          </button>

          <button
            type="button"
            className="adgen-audio-btn adgen-audio-btn--icon"
            onClick={toggleMute}
            title={isMuted ? "Bật âm thanh" : "Tắt tiếng"}
          >
            {isMuted ? <FiVolumeX /> : <FiVolume2 />}
          </button>

          <button
            type="button"
            className="adgen-audio-btn adgen-audio-btn--icon"
            onClick={handleReset}
            title="Nghe lại từ đầu"
          >
            <FiRotateCcw />
          </button>

          {(downloadUrl || src) && (
            <button
              type="button"
              onClick={handleDirectDownload}
              className="adgen-audio-btn adgen-audio-btn--icon"
              title="Tải file MP3 về máy"
              disabled={isDownloading}
            >
              {isDownloading ? <FiLoader className="adgen-spinner" /> : <FiDownload />}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}