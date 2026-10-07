import { useState, useRef, useEffect } from "react";
import {
  FiPlay,
  FiPause,
  FiDownload,
  FiVolume2,
  FiVolumeX,
  FiRotateCcw,
  FiMic,
} from "react-icons/fi";
import { fetchVoiceoverAudio } from "../../../services/api/voiceoverApi";
import "./VoiceoverModal.css";

export default function AudioPlayer({
  src,
  voiceName = "Voiceover",
  duration = 0,
  downloadUrl = null,
  compact = false,
}) {
  const audioRef = useRef(null);
  const [resolvedAudio, setResolvedAudio] = useState(null);
  const [loadErrorSrc, setLoadErrorSrc] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [totalDuration, setTotalDuration] = useState(duration || 0);
  const [isMuted, setIsMuted] = useState(false);
  const [playbackRate, setPlaybackRate] = useState(1.0);

  useEffect(() => {
    let active = true;
    let objectUrl = null;
    if (!src) return undefined;
    fetchVoiceoverAudio(src)
      .then((blob) => {
        if (!active) return;
        objectUrl = URL.createObjectURL(blob);
        setResolvedAudio({ source: src, url: objectUrl });
      })
      .catch((error) => {
        if (!active) return;
        console.error("Audio loading error:", error);
        setLoadErrorSrc(src);
      });

    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [src]);

  const resolvedSrc = resolvedAudio?.source === src ? resolvedAudio.url : null;
  const loadError = loadErrorSrc === src;

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio || !resolvedSrc) return undefined;

    const resetId = window.setTimeout(() => {
      setIsPlaying(false);
      setCurrentTime(0);
      if (duration) setTotalDuration(duration);
    }, 0);

    const handlePlay = () => setIsPlaying(true);
    const handlePause = () => setIsPlaying(false);
    const handleTimeUpdate = () => setCurrentTime(audio.currentTime);
    const handleLoadedMetadata = () => {
      if (audio.duration && !Number.isNaN(audio.duration) && audio.duration !== Infinity) {
        setTotalDuration(audio.duration);
      }
    };
    const handleEnded = () => {
      setIsPlaying(false);
      setCurrentTime(0);
    };
    const handleError = (event) => {
      console.warn("Audio element error:", event);
      setIsPlaying(false);
      setLoadErrorSrc(src);
    };

    audio.addEventListener("play", handlePlay);
    audio.addEventListener("pause", handlePause);
    audio.addEventListener("timeupdate", handleTimeUpdate);
    audio.addEventListener("loadedmetadata", handleLoadedMetadata);
    audio.addEventListener("ended", handleEnded);
    audio.addEventListener("error", handleError);
    audio.load();

    return () => {
      window.clearTimeout(resetId);
      audio.removeEventListener("play", handlePlay);
      audio.removeEventListener("pause", handlePause);
      audio.removeEventListener("timeupdate", handleTimeUpdate);
      audio.removeEventListener("loadedmetadata", handleLoadedMetadata);
      audio.removeEventListener("ended", handleEnded);
      audio.removeEventListener("error", handleError);
    };
  }, [resolvedSrc, duration, src]);

  const togglePlay = () => {
    const audio = audioRef.current;
    if (!audio || !resolvedSrc) return;
    if (audio.ended) audio.currentTime = 0;
    if (audio.paused) {
      audio.play().catch((error) => console.error("Audio playback error:", error));
    } else {
      audio.pause();
    }
  };

  const handleSeek = (event) => {
    const time = Number(event.target.value);
    setCurrentTime(time);
    if (audioRef.current) audioRef.current.currentTime = time;
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
    const nextRate = rates[(rates.indexOf(playbackRate) + 1) % rates.length];
    setPlaybackRate(nextRate);
    if (audioRef.current) audioRef.current.playbackRate = nextRate;
  };

  const handleDownload = async (event) => {
    event.preventDefault();
    const targetUrl = downloadUrl || src;
    if (!targetUrl) return;
    try {
      const blob = await fetchVoiceoverAudio(targetUrl);
      const objectUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      const filename = targetUrl.split("/").pop().split("?")[0] || "voiceover.mp3";
      link.href = objectUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 0);
    } catch (error) {
      console.error("Download audio error:", error);
    }
  };

  const formatTime = (seconds) => {
    if (seconds == null || Number.isNaN(seconds) || seconds < 0) return "0:00";
    const minutes = Math.floor(seconds / 60);
    const secondsPart = Math.floor(seconds % 60);
    return `${minutes}:${secondsPart < 10 ? "0" : ""}${secondsPart}`;
  };

  const rawPercent = totalDuration > 0 ? (currentTime / totalDuration) * 100 : 0;
  const progressPercent = Math.min(Math.max(Number.isNaN(rawPercent) ? 0 : rawPercent, 0), 100);
  const displayVoice = voiceName || "Voiceover";

  if (!src) return null;

  return (
    <div className={`adgen-audio-player ${compact ? "adgen-audio-player--compact" : ""}`}>
      {resolvedSrc && <audio ref={audioRef} src={resolvedSrc} preload="metadata" />}
      <div className="adgen-audio-player__main">
        <button
          type="button"
          className="adgen-audio-btn adgen-audio-btn--play"
          onClick={togglePlay}
          disabled={!resolvedSrc || loadError}
          title={isPlaying ? "Tạm dừng" : "Phát"}
          aria-label={isPlaying ? "Tạm dừng" : "Phát"}
        >
          {isPlaying ? <FiPause /> : <FiPlay />}
        </button>

        <div className="adgen-audio-player__content">
          <div className="adgen-audio-player__header">
            <span className="adgen-audio-player__badge"><FiMic aria-hidden="true" /> Voiceover</span>
            <span className="adgen-audio-player__voice" title={displayVoice}>{displayVoice}</span>
          </div>
          {loadError && <small>Không thể tải audio. Vui lòng tạo lại voiceover.</small>}
          {!resolvedSrc && !loadError && <small>Đang tải audio...</small>}
          <div className="adgen-audio-player__progress-wrap">
            <input
              type="range"
              min="0"
              max={totalDuration || 1}
              step="0.1"
              value={currentTime}
              onChange={handleSeek}
              disabled={!resolvedSrc || loadError}
              className="adgen-audio-player__seekbar"
              style={{ background: `linear-gradient(to right, var(--color-primary-500, #3b82f6) ${progressPercent}%, var(--color-gray-700, #374151) ${progressPercent}%)` }}
            />
            <div className="adgen-audio-player__time">
              <span>{formatTime(currentTime)}</span><span>/</span><span>{formatTime(totalDuration)}</span>
            </div>
          </div>
        </div>

        <div className="adgen-audio-player__actions">
          <button type="button" className="adgen-audio-btn adgen-audio-btn--icon" onClick={cyclePlaybackRate} title={`Tốc độ phát (${playbackRate}x)`}>
            <span className="adgen-audio-speed-tag">{playbackRate}x</span>
          </button>
          <button type="button" className="adgen-audio-btn adgen-audio-btn--icon" onClick={toggleMute} title={isMuted ? "Bật âm thanh" : "Tắt tiếng"} disabled={!resolvedSrc || loadError}>
            {isMuted ? <FiVolumeX /> : <FiVolume2 />}
          </button>
          <button type="button" className="adgen-audio-btn adgen-audio-btn--icon" onClick={handleReset} title="Nghe lại từ đầu" disabled={!resolvedSrc || loadError}>
            <FiRotateCcw />
          </button>
          <button type="button" onClick={handleDownload} className="adgen-audio-btn adgen-audio-btn--icon" title="Tải file MP3 về máy" disabled={loadError || !src}>
            <FiDownload />
          </button>
        </div>
      </div>
    </div>
  );
}
