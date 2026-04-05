"use client";

import { useEffect, useMemo, useState } from "react";
import type { Alert, StreamFrame } from "@/lib/api";
import {
  REPLAY_DEFAULT_LAG_FRAMES,
  REPLAY_WINDOWS,
  highestSeverity,
  timeLabel as defaultTimeLabel,
} from "@/utils/dashboard";

export type ReplayMarker = {
  id: string;
  index: number;
  severity: "critical" | "warning" | "info";
  label: string;
  time: string;
};

type UseReplayControllerArgs = {
  frame: StreamFrame | null;
  history: StreamFrame[];
  initialWindowMinutes?: (typeof REPLAY_WINDOWS)[number];
  timeLabel?: (value: string) => string;
};

export function useReplayController({
  frame,
  history,
  initialWindowMinutes = 10,
  timeLabel = defaultTimeLabel,
}: UseReplayControllerArgs) {
  const [viewMode, setViewMode] = useState<"live" | "replay">("live");
  const [replayWindowMinutes, setReplayWindowMinutes] =
    useState<(typeof REPLAY_WINDOWS)[number]>(initialWindowMinutes);
  const [replayIndex, setReplayIndex] = useState(0);
  const [playbackPaused, setPlaybackPaused] = useState(false);
  const [replayLagFrames, setReplayLagFrames] = useState(REPLAY_DEFAULT_LAG_FRAMES);
  const [pausedFrame, setPausedFrame] = useState<StreamFrame | null>(null);
  const [pausedHistory, setPausedHistory] = useState<StreamFrame[]>([]);
  const [pausedReplayFrames, setPausedReplayFrames] = useState<StreamFrame[]>([]);
  const [pausedReplayTimestamp, setPausedReplayTimestamp] = useState<string | null>(null);

  const liveReplayFrames = useMemo(() => {
    const frameLimit = replayWindowMinutes * 60;
    return history.slice(-frameLimit);
  }, [history, replayWindowMinutes]);

  const replayFrames =
    playbackPaused && viewMode === "replay" && pausedReplayFrames.length > 0
      ? pausedReplayFrames
      : liveReplayFrames;

  useEffect(() => {
    if (viewMode !== "replay") return;
    setReplayIndex((current) => Math.min(current, Math.max(replayFrames.length - 1, 0)));
  }, [replayFrames.length, viewMode]);

  useEffect(() => {
    if (viewMode !== "replay" || playbackPaused) return;
    const maxIndex = Math.max(replayFrames.length - 1, 0);
    setReplayIndex(Math.max(0, maxIndex - replayLagFrames));
  }, [replayFrames.length, replayLagFrames, playbackPaused, viewMode]);

  const selectedReplayIndex = useMemo(() => {
    const maxIndex = Math.max(replayFrames.length - 1, 0);
    if (!(playbackPaused && viewMode === "replay" && pausedReplayTimestamp)) {
      return Math.min(replayIndex, maxIndex);
    }

    const targetTime = new Date(pausedReplayTimestamp).getTime();
    if (!Number.isFinite(targetTime)) {
      return Math.min(replayIndex, maxIndex);
    }

    let bestIndex = 0;
    for (let index = 0; index < replayFrames.length; index += 1) {
      const frameTime = new Date(replayFrames[index]?.telemetry.timestamp ?? "").getTime();
      if (!Number.isFinite(frameTime)) continue;
      if (frameTime <= targetTime) {
        bestIndex = index;
      } else {
        break;
      }
    }

    return Math.min(bestIndex, maxIndex);
  }, [pausedReplayTimestamp, playbackPaused, replayFrames, replayIndex, viewMode]);
  const replayFrame =
    viewMode === "replay"
      ? replayFrames[selectedReplayIndex] ?? replayFrames[replayFrames.length - 1] ?? frame
      : null;
  const liveFrame = playbackPaused ? pausedFrame ?? frame : frame;
  const activeFrame = viewMode === "replay" ? replayFrame ?? liveFrame : liveFrame;
  const activeHistory =
    viewMode === "replay"
      ? replayFrames.slice(0, Math.max(selectedReplayIndex + 1, 1))
      : playbackPaused
        ? pausedHistory
        : history;

  const replayMarkers = useMemo<ReplayMarker[]>(() => {
    const previousAlertIds = new Set<string>();

    return replayFrames.flatMap((entry, index) => {
      const newAlerts = entry.alerts.filter((alert) => !previousAlertIds.has(alert.id));
      entry.alerts.forEach((alert) => previousAlertIds.add(alert.id));

      if (newAlerts.length === 0) {
        return [];
      }

      return [
        {
          id: `${entry.telemetry.timestamp}-${newAlerts.map((alert) => alert.id).join("-")}`,
          index,
          severity: highestSeverity(newAlerts as Alert[]),
          label: newAlerts[0]?.title ?? "Алерт",
          time: timeLabel(entry.telemetry.timestamp),
        },
      ];
    });
  }, [replayFrames, timeLabel]);

  const enterLiveMode = () => {
    setViewMode("live");
    setPlaybackPaused(false);
    setPausedReplayTimestamp(null);
  };

  const enterReplayMode = () => {
    const maxIndex = Math.max(replayFrames.length - 1, 0);
    const defaultLag = Math.min(REPLAY_DEFAULT_LAG_FRAMES, maxIndex);
    setViewMode("replay");
    setPlaybackPaused(false);
    setReplayLagFrames(defaultLag);
    setReplayIndex(Math.max(0, maxIndex - defaultLag));
    setPausedReplayTimestamp(null);
  };

  const handleReplayWindowChange = (minutes: (typeof REPLAY_WINDOWS)[number]) => {
    setReplayWindowMinutes(minutes);
    setReplayIndex((current) => Math.max(Math.min(current, minutes * 60 - 1), 0));
  };

  const handleReplaySliderChange = (nextIndex: number) => {
    const maxIndex = Math.max(replayFrames.length - 1, 0);
    setViewMode("replay");
    setReplayIndex(nextIndex);
    setReplayLagFrames(Math.max(0, maxIndex - nextIndex));
    setPausedReplayTimestamp(null);
  };

  const togglePlaybackPause = () => {
    setPlaybackPaused((current) => {
      const next = !current;
      if (next) {
        setPausedFrame(frame ?? null);
        setPausedHistory(history);
        if (viewMode === "replay") {
          setPausedReplayFrames(liveReplayFrames);
          const replayFrame =
            liveReplayFrames[Math.min(replayIndex, Math.max(liveReplayFrames.length - 1, 0))] ??
            liveReplayFrames[liveReplayFrames.length - 1] ??
            frame;
          setPausedReplayTimestamp(replayFrame?.telemetry.timestamp ?? null);
        }
      } else {
        setPausedReplayFrames([]);
        setPausedReplayTimestamp(null);
      }
      return next;
    });
  };

  return {
    viewMode,
    replayWindowMinutes,
    playbackPaused,
    setPlaybackPaused,
    togglePlaybackPause,
    replayFrames,
    selectedReplayIndex,
    activeFrame,
    activeHistory,
    replayMarkers,
    enterLiveMode,
    enterReplayMode,
    handleReplayWindowChange,
    handleReplaySliderChange,
  };
}
