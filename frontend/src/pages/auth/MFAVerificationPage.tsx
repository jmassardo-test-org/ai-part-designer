/**
 * MFA Verification Page
 * 
 * Displayed during login when user has MFA enabled.
 * User enters their TOTP code or backup code to complete login.
 */

import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Shield, KeyRound, AlertCircle, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { mfaApi } from '@/lib/api/mfa';
import { useAuth } from '@/contexts/AuthContext';

/**
 * MFA Verification page shown after initial login credentials are validated.
 */
export default function MFAVerificationPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login: authLogin } = useAuth();
  
  // Get email from location state (passed from login page)
  const email = (location.state as { email?: string })?.email || '';
  
  const [totpCode, setTotpCode] = useState('');
  const [backupCode, setBackupCode] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'totp' | 'backup'>('totp');
  
  const handleTotpSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!totpCode || totpCode.length !== 6) {
      setError('Please enter a 6-digit code');
      return;
    }
    
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await mfaApi.loginWithMFA({
        email,
        code: totpCode,
      });
      
      // Store tokens and complete login
      authLogin(response.access_token, response.refresh_token);
      navigate('/dashboard');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid verification code. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleBackupSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!backupCode || backupCode.length !== 8) {
      setError('Please enter an 8-character backup code');
      return;
    }
    
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await mfaApi.loginWithMFA({
        email,
        code: backupCode,
      });
      
      // Store tokens and complete login
      authLogin(response.access_token, response.refresh_token);
      navigate('/dashboard');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid backup code. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleCodeChange = (value: string, type: 'totp' | 'backup') => {
    // Only allow digits for TOTP, alphanumeric for backup
    const sanitized = type === 'totp' 
      ? value.replace(/\D/g, '').slice(0, 6)
      : value.replace(/[^a-zA-Z0-9]/g, '').toUpperCase().slice(0, 8);
    
    if (type === 'totp') {
      setTotpCode(sanitized);
    } else {
      setBackupCode(sanitized);
    }
    setError(null);
  };
  
  if (!email) {
    // Redirect to login if no email in state
    navigate('/login');
    return null;
  }
  
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary/5 to-secondary/5 px-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            <div className="p-3 rounded-full bg-primary/10">
              <Shield className="h-8 w-8 text-primary" />
            </div>
          </div>
          <CardTitle className="text-2xl">Two-Factor Authentication</CardTitle>
          <CardDescription>
            Enter the verification code from your authenticator app
          </CardDescription>
        </CardHeader>
        
        <CardContent>
          {error && (
            <Alert variant="destructive" className="mb-4">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          
          <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as 'totp' | 'backup')}>
            <TabsList className="grid w-full grid-cols-2 mb-4">
              <TabsTrigger value="totp" className="flex items-center gap-2">
                <RefreshCw className="h-4 w-4" />
                Authenticator
              </TabsTrigger>
              <TabsTrigger value="backup" className="flex items-center gap-2">
                <KeyRound className="h-4 w-4" />
                Backup Code
              </TabsTrigger>
            </TabsList>
            
            <TabsContent value="totp">
              <form onSubmit={handleTotpSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="totp-code">6-Digit Code</Label>
                  <Input
                    id="totp-code"
                    type="text"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    value={totpCode}
                    onChange={(e) => handleCodeChange(e.target.value, 'totp')}
                    placeholder="000000"
                    className="text-center text-2xl tracking-widest font-mono"
                    autoFocus
                  />
                  <p className="text-xs text-muted-foreground text-center">
                    Open your authenticator app (Google Authenticator, Authy, etc.)
                    and enter the 6-digit code.
                  </p>
                </div>
                
                <Button
                  type="submit"
                  className="w-full"
                  disabled={isLoading || totpCode.length !== 6}
                >
                  {isLoading ? 'Verifying...' : 'Verify & Sign In'}
                </Button>
              </form>
            </TabsContent>
            
            <TabsContent value="backup">
              <form onSubmit={handleBackupSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="backup-code">Backup Code</Label>
                  <Input
                    id="backup-code"
                    type="text"
                    value={backupCode}
                    onChange={(e) => handleCodeChange(e.target.value, 'backup')}
                    placeholder="XXXXXXXX"
                    className="text-center text-xl tracking-widest font-mono uppercase"
                  />
                  <p className="text-xs text-muted-foreground text-center">
                    Enter one of your backup codes. Each code can only be used once.
                  </p>
                </div>
                
                <Button
                  type="submit"
                  className="w-full"
                  disabled={isLoading || backupCode.length !== 8}
                >
                  {isLoading ? 'Verifying...' : 'Use Backup Code'}
                </Button>
              </form>
            </TabsContent>
          </Tabs>
          
          <div className="mt-6 text-center">
            <Button
              variant="link"
              className="text-sm"
              onClick={() => navigate('/login')}
            >
              Back to login
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
