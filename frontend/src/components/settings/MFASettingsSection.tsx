/**
 * MFA Settings Section Component
 * 
 * Allows users to enable/disable MFA from their account settings.
 * Shows QR code for setup and backup codes.
 */

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Shield,
  ShieldCheck,
  ShieldOff,
  QrCode,
  KeyRound,
  Copy,
  Download,
  AlertCircle,
  CheckCircle,
} from 'lucide-react';
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { mfaApi, type MFASetupResponse } from '@/lib/api/mfa';
import { cn } from '@/lib/utils';

/**
 * MFA Settings section for account settings page.
 */
export function MFASettingsSection() {
  const queryClient = useQueryClient();
  
  const [showSetupDialog, setShowSetupDialog] = useState(false);
  const [showDisableDialog, setShowDisableDialog] = useState(false);
  const [showBackupCodesDialog, setShowBackupCodesDialog] = useState(false);
  const [setupData, setSetupData] = useState<MFASetupResponse | null>(null);
  const [verificationCode, setVerificationCode] = useState('');
  const [disablePassword, setDisablePassword] = useState('');
  const [disableCode, setDisableCode] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  
  // Query MFA status
  const { data: status, isLoading } = useQuery({
    queryKey: ['mfa', 'status'],
    queryFn: () => mfaApi.getStatus(),
  });
  
  // Setup mutation
  const setupMutation = useMutation({
    mutationFn: () => mfaApi.setup(),
    onSuccess: (data) => {
      setSetupData(data);
      setShowSetupDialog(true);
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || 'Failed to start MFA setup');
    },
  });
  
  // Enable mutation
  const enableMutation = useMutation({
    mutationFn: (code: string) => mfaApi.enable(code),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mfa'] });
      setShowSetupDialog(false);
      setSetupData(null);
      setVerificationCode('');
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || 'Invalid verification code');
    },
  });
  
  // Disable mutation
  const disableMutation = useMutation({
    mutationFn: (data: { password: string; code: string }) => mfaApi.disable(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mfa'] });
      setShowDisableDialog(false);
      setDisablePassword('');
      setDisableCode('');
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || 'Failed to disable MFA');
    },
  });
  
  // Regenerate backup codes mutation
  const regenerateMutation = useMutation({
    mutationFn: () => mfaApi.regenerateBackupCodes(),
    onSuccess: (data) => {
      setSetupData((prev) => prev ? { ...prev, backup_codes: data.backup_codes } : null);
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || 'Failed to regenerate backup codes');
    },
  });
  
  const handleStartSetup = () => {
    setError(null);
    setupMutation.mutate();
  };
  
  const handleVerifyAndEnable = () => {
    if (verificationCode.length !== 6) {
      setError('Please enter a 6-digit code');
      return;
    }
    setError(null);
    enableMutation.mutate(verificationCode);
  };
  
  const handleDisable = () => {
    if (!disablePassword || !disableCode) {
      setError('Please enter your password and verification code');
      return;
    }
    setError(null);
    disableMutation.mutate({ password: disablePassword, code: disableCode });
  };
  
  const copyToClipboard = async (text: string, index: number) => {
    await navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };
  
  const downloadBackupCodes = () => {
    if (!setupData?.backup_codes) return;
    
    const content = [
      'AssemblematicAI - MFA Backup Codes',
      '================================',
      '',
      'Keep these codes safe. Each code can only be used once.',
      '',
      ...setupData.backup_codes.map((code, i) => `${i + 1}. ${code}`),
      '',
      `Generated: ${new Date().toISOString()}`,
    ].join('\n');
    
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'assemblematic-mfa-backup-codes.txt';
    a.click();
    URL.revokeObjectURL(url);
  };
  
  if (isLoading) {
    return (
      <Card>
        <CardContent className="py-8 text-center">
          <p className="text-muted-foreground">Loading MFA settings...</p>
        </CardContent>
      </Card>
    );
  }
  
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Shield className="h-6 w-6 text-primary" />
            <div>
              <CardTitle>Two-Factor Authentication</CardTitle>
              <CardDescription>
                Add an extra layer of security to your account
              </CardDescription>
            </div>
          </div>
          <Badge variant={status?.enabled ? 'default' : 'secondary'}>
            {status?.enabled ? (
              <span className="flex items-center gap-1">
                <ShieldCheck className="h-3 w-3" />
                Enabled
              </span>
            ) : (
              <span className="flex items-center gap-1">
                <ShieldOff className="h-3 w-3" />
                Disabled
              </span>
            )}
          </Badge>
        </div>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {status?.enabled ? (
          <>
            <Alert>
              <CheckCircle className="h-4 w-4 text-green-500" />
              <AlertTitle>MFA is enabled</AlertTitle>
              <AlertDescription>
                Your account is protected with two-factor authentication.
                {status.backup_codes_remaining > 0 && (
                  <span className="block mt-1">
                    You have {status.backup_codes_remaining} backup codes remaining.
                  </span>
                )}
              </AlertDescription>
            </Alert>
            
            <div className="flex gap-3">
              <Button
                variant="outline"
                onClick={() => setShowBackupCodesDialog(true)}
              >
                <KeyRound className="h-4 w-4 mr-2" />
                View Backup Codes
              </Button>
              <Button
                variant="destructive"
                onClick={() => setShowDisableDialog(true)}
              >
                <ShieldOff className="h-4 w-4 mr-2" />
                Disable MFA
              </Button>
            </div>
          </>
        ) : (
          <>
            <p className="text-sm text-muted-foreground">
              Protect your account by requiring a verification code from your 
              authenticator app when signing in.
            </p>
            
            <Button onClick={handleStartSetup} disabled={setupMutation.isPending}>
              <Shield className="h-4 w-4 mr-2" />
              {setupMutation.isPending ? 'Setting up...' : 'Enable MFA'}
            </Button>
          </>
        )}
      </CardContent>
      
      {/* Setup Dialog */}
      <Dialog open={showSetupDialog} onOpenChange={setShowSetupDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <QrCode className="h-5 w-5" />
              Set Up Two-Factor Authentication
            </DialogTitle>
            <DialogDescription>
              Scan this QR code with your authenticator app
            </DialogDescription>
          </DialogHeader>
          
          {setupData && (
            <div className="space-y-6">
              {/* QR Code */}
              <div className="flex justify-center">
                <div className="p-4 bg-white rounded-lg">
                  <img
                    src={`data:image/png;base64,${setupData.qr_code}`}
                    alt="MFA QR Code"
                    className="w-48 h-48"
                  />
                </div>
              </div>
              
              {/* Manual Entry */}
              <div className="space-y-2">
                <Label className="text-sm text-muted-foreground">
                  Or enter this code manually:
                </Label>
                <div className="flex items-center gap-2">
                  <code className="flex-1 p-2 bg-muted rounded text-sm font-mono break-all">
                    {setupData.secret}
                  </code>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => copyToClipboard(setupData.secret, -1)}
                  >
                    <Copy className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              
              {/* Verification */}
              <div className="space-y-2">
                <Label htmlFor="verify-code">Enter verification code</Label>
                <Input
                  id="verify-code"
                  type="text"
                  inputMode="numeric"
                  value={verificationCode}
                  onChange={(e) => {
                    setVerificationCode(e.target.value.replace(/\D/g, '').slice(0, 6));
                    setError(null);
                  }}
                  placeholder="000000"
                  className="text-center text-xl tracking-widest font-mono"
                />
              </div>
              
              {/* Backup Codes */}
              <Alert>
                <KeyRound className="h-4 w-4" />
                <AlertTitle>Save your backup codes</AlertTitle>
                <AlertDescription>
                  These codes can be used if you lose access to your authenticator app.
                  Each code can only be used once.
                </AlertDescription>
              </Alert>
              
              <div className="grid grid-cols-2 gap-2">
                {setupData.backup_codes.map((code, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between p-2 bg-muted rounded font-mono text-sm"
                  >
                    <span>{code}</span>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-6 w-6 p-0"
                      onClick={() => copyToClipboard(code, index)}
                    >
                      {copiedIndex === index ? (
                        <CheckCircle className="h-3 w-3 text-green-500" />
                      ) : (
                        <Copy className="h-3 w-3" />
                      )}
                    </Button>
                  </div>
                ))}
              </div>
              
              <Button
                variant="outline"
                className="w-full"
                onClick={downloadBackupCodes}
              >
                <Download className="h-4 w-4 mr-2" />
                Download Backup Codes
              </Button>
              
              {error && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}
            </div>
          )}
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowSetupDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleVerifyAndEnable}
              disabled={verificationCode.length !== 6 || enableMutation.isPending}
            >
              {enableMutation.isPending ? 'Enabling...' : 'Verify & Enable MFA'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* Disable Dialog */}
      <Dialog open={showDisableDialog} onOpenChange={setShowDisableDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-600">
              <ShieldOff className="h-5 w-5" />
              Disable Two-Factor Authentication
            </DialogTitle>
            <DialogDescription>
              This will remove the extra security from your account.
              You'll need to enter your password and a verification code to confirm.
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="disable-password">Password</Label>
              <Input
                id="disable-password"
                type="password"
                value={disablePassword}
                onChange={(e) => setDisablePassword(e.target.value)}
                placeholder="Enter your password"
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="disable-code">Verification Code</Label>
              <Input
                id="disable-code"
                type="text"
                value={disableCode}
                onChange={(e) => {
                  setDisableCode(e.target.value.replace(/[^a-zA-Z0-9]/g, '').slice(0, 8));
                  setError(null);
                }}
                placeholder="6-digit code or backup code"
                className="font-mono"
              />
            </div>
            
            {error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDisableDialog(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDisable}
              disabled={!disablePassword || !disableCode || disableMutation.isPending}
            >
              {disableMutation.isPending ? 'Disabling...' : 'Disable MFA'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* Backup Codes Dialog */}
      <Dialog open={showBackupCodesDialog} onOpenChange={setShowBackupCodesDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <KeyRound className="h-5 w-5" />
              Backup Codes
            </DialogTitle>
            <DialogDescription>
              Use these codes if you lose access to your authenticator app.
              {status?.backup_codes_remaining !== undefined && (
                <span className="block mt-1">
                  You have {status.backup_codes_remaining} codes remaining.
                </span>
              )}
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                For security, backup codes are only shown when MFA is first enabled.
                If you need new codes, you can regenerate them below.
              </AlertDescription>
            </Alert>
            
            <Button
              variant="outline"
              className="w-full"
              onClick={() => regenerateMutation.mutate()}
              disabled={regenerateMutation.isPending}
            >
              {regenerateMutation.isPending ? 'Regenerating...' : 'Regenerate Backup Codes'}
            </Button>
          </div>
          
          <DialogFooter>
            <Button onClick={() => setShowBackupCodesDialog(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}
