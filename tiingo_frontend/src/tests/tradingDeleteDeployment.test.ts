import { describe, expect, it, vi } from 'vitest';

describe('executionApi.deleteDeployment', () => {
  it('sends close_positions in delete request body', async () => {
    const deleteMock = vi.fn().mockResolvedValue({ data: { deleted: true } });
    vi.doMock('../api/client', () => ({
      api: { delete: deleteMock },
    }));

    const { executionApi } = await import('../api/endpoints');
    await executionApi.deleteDeployment('dep-1', { close_positions: true });

    expect(deleteMock).toHaveBeenCalledWith('/execution/deployments/dep-1', {
      data: { close_positions: true },
    });

    vi.resetModules();
    vi.doUnmock('../api/client');
  });
});
