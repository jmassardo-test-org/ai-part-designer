/**
 * OAuth API client
 * 
 * This is a placeholder file created to satisfy existing imports.
 * The actual implementation should be added when OAuth functionality is needed.
 */

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export interface OAuthConnection {
  provider: string;
  email?: string;
  connected_at: string;
  provider_email?: string;
  provider_username?: string;
}

export interface OAuthConnectionsResponse {
  connections: OAuthConnection[];
}

export interface OAuthLinkResponse {
  authorization_url: string;
  state?: string;
}

export interface OAuthLoginResponse {
  authorization_url: string;
  state?: string;
}

export const oauthApi = {
  async getConnections(): Promise<OAuthConnectionsResponse> {
    const token = localStorage.getItem('token');
    const response = await fetch(`${API_BASE}/auth/oauth/connections`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
    if (!response.ok) {
      throw new Error('Failed to fetch OAuth connections');
    }
    return response.json();
  },

  async initiateLogin(provider: string, redirectUri?: string): Promise<OAuthLoginResponse> {
    const params = redirectUri ? `?redirect_uri=${encodeURIComponent(redirectUri)}` : '';
    const response = await fetch(`${API_BASE}/auth/oauth/${provider}/login${params}`, {
      method: 'POST',
    });
    if (!response.ok) {
      throw new Error(`Failed to initiate ${provider} login`);
    }
    return response.json();
  },

  async initiateLink(provider: string): Promise<OAuthLinkResponse> {
    const token = localStorage.getItem('token');
    const response = await fetch(`${API_BASE}/auth/oauth/link/${provider}`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
    if (!response.ok) {
      throw new Error(`Failed to initiate ${provider} link`);
    }
    return response.json();
  },

  async disconnect(provider: string): Promise<{ message: string }> {
    const token = localStorage.getItem('token');
    const response = await fetch(`${API_BASE}/auth/oauth/disconnect/${provider}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
    if (!response.ok) {
      throw new Error(`Failed to disconnect ${provider}`);
    }
    return { message: `${provider} disconnected successfully` };
  },

  async unlinkProvider(provider: string): Promise<{ message: string }> {
    const token = localStorage.getItem('token');
    const response = await fetch(`${API_BASE}/auth/oauth/unlink/${provider}`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
    if (!response.ok) {
      throw new Error(`Failed to unlink ${provider}`);
    }
    return { message: `${provider} unlinked successfully` };
  },
};
