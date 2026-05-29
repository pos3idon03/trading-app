import { describe, expect, it, vi } from 'vitest';
import {
  CANDLE_STYLE_PRESETS,
  buildChartOptions,
  getStyleColors,
  supportsOhlcMarkers,
  zoomTimeScale,
} from '../utils/ohlcvChartConfig';

describe('ohlcvChartConfig', () => {
  it('enables scroll and scale interactions', () => {
    const options = buildChartOptions(800, 520);
    const scroll = options.handleScroll as { mouseWheel?: boolean; pressedMouseMove?: boolean };
    const scale = options.handleScale as { mouseWheel?: boolean };
    expect(scroll.mouseWheel).toBe(true);
    expect(scroll.pressedMouseMove).toBe(true);
    expect(scale.mouseWheel).toBe(true);
    expect(options.timeScale?.rightOffset).toBe(12);
    expect(options.timeScale?.fixLeftEdge).toBe(false);
    expect(options.timeScale?.fixRightEdge).toBe(false);
  });

  it('returns preset colors', () => {
    const classic = getStyleColors('classic');
    expect(classic.upColor).toBe(CANDLE_STYLE_PRESETS.classic.upColor);
    expect(classic.downColor).toBe(CANDLE_STYLE_PRESETS.classic.downColor);
  });

  it('marks ohlc marker support by chart type', () => {
    expect(supportsOhlcMarkers('candlestick')).toBe(true);
    expect(supportsOhlcMarkers('bar')).toBe(true);
    expect(supportsOhlcMarkers('line')).toBe(false);
    expect(supportsOhlcMarkers('area')).toBe(false);
  });

  it('computes zoomed logical range around center', () => {
    const setRange = vi.fn();
    const chart = {
      timeScale: () => ({
        getVisibleLogicalRange: () => ({ from: 0, to: 100 }),
        setVisibleLogicalRange: setRange,
        fitContent: vi.fn(),
      }),
    };

    zoomTimeScale(chart as never, 0.5, 200);

    expect(setRange).toHaveBeenCalledWith({ from: 25, to: 75 });
  });

  it('clamps zoom span to minimum bar count', () => {
    const setRange = vi.fn();
    const chart = {
      timeScale: () => ({
        getVisibleLogicalRange: () => ({ from: 10, to: 12 }),
        setVisibleLogicalRange: setRange,
        fitContent: vi.fn(),
      }),
    };

    zoomTimeScale(chart as never, 0.5, 50);

    expect(setRange).toHaveBeenCalledWith({ from: 8.5, to: 13.5 });
  });
});
