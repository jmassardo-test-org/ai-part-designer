/**
 * Admin Moderation Panel Page
 * 
 * Provides admin interface for content moderation, including:
 * - Reports queue with review actions
 * - Active bans management
 * - Moderation statistics dashboard
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { formatDistanceToNow } from 'date-fns';
import {
  Flag,
  Ban,
  Shield,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Eye,
  EyeOff,
  UserX,
  RefreshCw,
} from 'lucide-react';
import { useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import {
  moderationApi,
  type ReportDetailResponse,
  type BanDetailResponse,
  type ModerationStats,
} from '@/lib/api/moderation';

/**
 * Moderation Stats Cards
 */
function StatsCards({ stats }: { stats: ModerationStats }) {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Pending Reports</CardTitle>
          <AlertTriangle className="h-4 w-4 text-yellow-500" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.pending_reports}</div>
          <p className="text-xs text-muted-foreground">Awaiting review</p>
        </CardContent>
      </Card>
      
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Reports Today</CardTitle>
          <Flag className="h-4 w-4 text-orange-500" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.reports_today}</div>
          <p className="text-xs text-muted-foreground">New today</p>
        </CardContent>
      </Card>
      
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Weekly Reports</CardTitle>
          <Flag className="h-4 w-4 text-blue-500" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.reports_this_week}</div>
          <p className="text-xs text-muted-foreground">Last 7 days</p>
        </CardContent>
      </Card>
      
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Active Bans</CardTitle>
          <Ban className="h-4 w-4 text-red-500" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.active_bans}</div>
          <p className="text-xs text-muted-foreground">Currently banned</p>
        </CardContent>
      </Card>
      
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Hidden Comments</CardTitle>
          <EyeOff className="h-4 w-4 text-gray-500" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.hidden_comments}</div>
          <p className="text-xs text-muted-foreground">Moderated</p>
        </CardContent>
      </Card>
    </div>
  );
}

/**
 * Reports Queue Table
 */
function ReportsQueue() {
  const queryClient = useQueryClient();
  const [selectedReport, setSelectedReport] = useState<ReportDetailResponse | null>(null);
  const [action, setAction] = useState<string>('');
  const [notes, setNotes] = useState('');
  
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['moderation', 'reports'],
    queryFn: () => moderationApi.getPendingReports(),
  });
  
  const resolveMutation = useMutation({
    mutationFn: async ({ reportId, action, notes }: { reportId: string; action: string; notes?: string }) => {
      return moderationApi.resolveReport(reportId, { action: action as 'dismiss' | 'warn' | 'hide_content' | 'remove_content' | 'ban_user', resolution_notes: notes });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['moderation'] });
      setSelectedReport(null);
      setAction('');
      setNotes('');
    },
  });
  
  const dismissMutation = useMutation({
    mutationFn: async ({ reportId, notes }: { reportId: string; notes?: string }) => {
      return moderationApi.dismissReport(reportId, notes);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['moderation'] });
      setSelectedReport(null);
      setNotes('');
    },
  });
  
  const reasonLabels: Record<string, string> = {
    spam: 'Spam',
    inappropriate: 'Inappropriate',
    copyright: 'Copyright',
    misleading: 'Misleading',
    offensive: 'Offensive',
    other: 'Other',
  };
  
  const targetLabels: Record<string, string> = {
    template: 'Template',
    comment: 'Comment',
    design: 'Design',
    user: 'User',
  };
  
  if (isLoading) {
    return <div className="text-center py-8">Loading reports...</div>;
  }
  
  const reports = data?.items || [];
  
  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold">Pending Reports</h3>
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>
      
      {reports.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <CheckCircle className="h-12 w-12 text-green-500 mb-4" />
            <p className="text-lg font-medium">All clear!</p>
            <p className="text-muted-foreground">No pending reports to review.</p>
          </CardContent>
        </Card>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Type</TableHead>
              <TableHead>Reason</TableHead>
              <TableHead>Reporter</TableHead>
              <TableHead>Submitted</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {reports.map((report: ReportDetailResponse) => (
              <TableRow key={report.id}>
                <TableCell>
                  <Badge variant="outline">
                    {targetLabels[report.target_type] || report.target_type}
                  </Badge>
                </TableCell>
                <TableCell>
                  <Badge variant="destructive">
                    {reasonLabels[report.reason] || report.reason}
                  </Badge>
                </TableCell>
                <TableCell>
                  <span className="text-sm">{report.reporter_name || 'Unknown'}</span>
                </TableCell>
                <TableCell>
                  <span className="text-sm text-muted-foreground">
                    {formatDistanceToNow(new Date(report.created_at), { addSuffix: true })}
                  </span>
                </TableCell>
                <TableCell>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setSelectedReport(report)}
                    >
                      <Eye className="h-4 w-4 mr-1" />
                      Review
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => dismissMutation.mutate({ reportId: report.id })}
                    >
                      <XCircle className="h-4 w-4" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
      
      {/* Report Review Dialog */}
      <Dialog open={!!selectedReport} onOpenChange={() => setSelectedReport(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Review Report</DialogTitle>
            <DialogDescription>
              Take action on this {selectedReport?.target_type} report.
            </DialogDescription>
          </DialogHeader>
          
          {selectedReport && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-muted-foreground">Target Type:</span>
                  <p className="font-medium">{targetLabels[selectedReport.target_type]}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">Reason:</span>
                  <p className="font-medium">{reasonLabels[selectedReport.reason]}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">Reporter:</span>
                  <p className="font-medium">{selectedReport.reporter_name}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">Reported:</span>
                  <p className="font-medium">
                    {formatDistanceToNow(new Date(selectedReport.created_at), { addSuffix: true })}
                  </p>
                </div>
              </div>
              
              {selectedReport.description && (
                <div>
                  <span className="text-muted-foreground text-sm">Description:</span>
                  <p className="mt-1 p-3 bg-muted rounded text-sm">
                    {selectedReport.description}
                  </p>
                </div>
              )}
              
              <div className="space-y-2">
                <Label>Action</Label>
                <Select value={action} onValueChange={setAction}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select action..." />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="dismiss">Dismiss (No action)</SelectItem>
                    <SelectItem value="warn">Warn User</SelectItem>
                    <SelectItem value="hide_content">Hide Content</SelectItem>
                    <SelectItem value="remove_content">Remove Content</SelectItem>
                    <SelectItem value="ban_user">Ban User</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <div className="space-y-2">
                <Label>Notes (optional)</Label>
                <Textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Add resolution notes..."
                />
              </div>
            </div>
          )}
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setSelectedReport(null)}>
              Cancel
            </Button>
            <Button
              disabled={!action || resolveMutation.isPending}
              onClick={() => {
                if (selectedReport && action) {
                  resolveMutation.mutate({
                    reportId: selectedReport.id,
                    action,
                    notes: notes || undefined,
                  });
                }
              }}
            >
              {resolveMutation.isPending ? 'Processing...' : 'Apply Action'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

/**
 * Active Bans Table
 */
function ActiveBans() {
  const queryClient = useQueryClient();
  const [selectedBan, setSelectedBan] = useState<BanDetailResponse | null>(null);
  const [unbanReason, setUnbanReason] = useState('');
  
  const { data, isLoading } = useQuery({
    queryKey: ['moderation', 'bans'],
    queryFn: () => moderationApi.getActiveBans(),
  });
  
  const unbanMutation = useMutation({
    mutationFn: async ({ banId, reason }: { banId: string; reason: string }) => {
      return moderationApi.unbanUser(banId, { reason });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['moderation'] });
      setSelectedBan(null);
      setUnbanReason('');
    },
  });
  
  if (isLoading) {
    return <div className="text-center py-8">Loading bans...</div>;
  }
  
  const bans = data?.items || [];
  
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Active Bans</h3>
      
      {bans.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <CheckCircle className="h-12 w-12 text-green-500 mb-4" />
            <p className="text-lg font-medium">No active bans</p>
            <p className="text-muted-foreground">All users are in good standing.</p>
          </CardContent>
        </Card>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>User</TableHead>
              <TableHead>Reason</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Expires</TableHead>
              <TableHead>Banned</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {bans.map((ban: BanDetailResponse) => (
              <TableRow key={ban.id}>
                <TableCell>
                  <div>
                    <p className="font-medium">{ban.user_name || 'Unknown'}</p>
                    <p className="text-sm text-muted-foreground">{ban.user_email}</p>
                  </div>
                </TableCell>
                <TableCell>
                  <p className="text-sm max-w-[200px] truncate" title={ban.reason}>
                    {ban.reason}
                  </p>
                </TableCell>
                <TableCell>
                  <Badge variant={ban.is_permanent ? 'destructive' : 'secondary'}>
                    {ban.is_permanent ? 'Permanent' : 'Temporary'}
                  </Badge>
                </TableCell>
                <TableCell>
                  {ban.is_permanent ? (
                    <span className="text-muted-foreground">Never</span>
                  ) : ban.expires_at ? (
                    <span className="text-sm">
                      {formatDistanceToNow(new Date(ban.expires_at), { addSuffix: true })}
                    </span>
                  ) : (
                    <span className="text-muted-foreground">—</span>
                  )}
                </TableCell>
                <TableCell>
                  <span className="text-sm text-muted-foreground">
                    {formatDistanceToNow(new Date(ban.created_at), { addSuffix: true })}
                  </span>
                </TableCell>
                <TableCell>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setSelectedBan(ban)}
                  >
                    Unban
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
      
      {/* Unban Dialog */}
      <Dialog open={!!selectedBan} onOpenChange={() => setSelectedBan(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Unban User</DialogTitle>
            <DialogDescription>
              Remove the ban for {selectedBan?.user_name || selectedBan?.user_email}.
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Reason for unbanning</Label>
              <Textarea
                value={unbanReason}
                onChange={(e) => setUnbanReason(e.target.value)}
                placeholder="Explain why this user should be unbanned..."
                className="min-h-[100px]"
              />
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setSelectedBan(null)}>
              Cancel
            </Button>
            <Button
              disabled={unbanReason.length < 5 || unbanMutation.isPending}
              onClick={() => {
                if (selectedBan) {
                  unbanMutation.mutate({
                    banId: selectedBan.id,
                    reason: unbanReason,
                  });
                }
              }}
            >
              {unbanMutation.isPending ? 'Processing...' : 'Unban User'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

/**
 * Ban User Form
 */
function BanUserForm() {
  const queryClient = useQueryClient();
  const [userId, setUserId] = useState('');
  const [reason, setReason] = useState('');
  const [isPermanent, setIsPermanent] = useState(false);
  const [durationDays, setDurationDays] = useState('7');
  
  const banMutation = useMutation({
    mutationFn: async () => {
      return moderationApi.banUser({
        user_id: userId,
        reason,
        is_permanent: isPermanent,
        duration_days: isPermanent ? undefined : parseInt(durationDays, 10),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['moderation'] });
      setUserId('');
      setReason('');
      setIsPermanent(false);
      setDurationDays('7');
    },
  });
  
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <UserX className="h-5 w-5" />
          Ban User
        </CardTitle>
        <CardDescription>
          Manually ban a user from the platform.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="userId">User ID</Label>
          <Input
            id="userId"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            placeholder="Enter user UUID..."
          />
        </div>
        
        <div className="space-y-2">
          <Label htmlFor="reason">Reason</Label>
          <Textarea
            id="reason"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Explain why this user is being banned..."
            className="min-h-[80px]"
          />
        </div>
        
        <div className="flex items-center space-x-2">
          <Checkbox
            id="permanent"
            checked={isPermanent}
            onCheckedChange={(checked) => setIsPermanent(checked as boolean)}
          />
          <Label htmlFor="permanent">Permanent ban</Label>
        </div>
        
        {!isPermanent && (
          <div className="space-y-2">
            <Label htmlFor="duration">Duration (days)</Label>
            <Input
              id="duration"
              type="number"
              min="1"
              max="365"
              value={durationDays}
              onChange={(e) => setDurationDays(e.target.value)}
            />
          </div>
        )}
        
        <Button
          onClick={() => banMutation.mutate()}
          disabled={!userId || reason.length < 10 || banMutation.isPending}
          className="w-full bg-red-600 hover:bg-red-700"
        >
          {banMutation.isPending ? 'Banning...' : 'Ban User'}
        </Button>
      </CardContent>
    </Card>
  );
}

/**
 * Main Moderation Panel Page
 */
export default function ModerationPanelPage() {
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['moderation', 'stats'],
    queryFn: () => moderationApi.getStats(),
  });
  
  return (
    <div className="container mx-auto py-8 space-y-8">
      <div className="flex items-center gap-3">
        <Shield className="h-8 w-8 text-primary" />
        <div>
          <h1 className="text-3xl font-bold">Moderation Panel</h1>
          <p className="text-muted-foreground">
            Review reports and manage user access
          </p>
        </div>
      </div>
      
      {/* Stats */}
      {statsLoading ? (
        <div className="text-center py-4">Loading statistics...</div>
      ) : stats ? (
        <StatsCards stats={stats} />
      ) : null}
      
      {/* Main Content */}
      <Tabs defaultValue="reports">
        <TabsList>
          <TabsTrigger value="reports" className="flex items-center gap-2">
            <Flag className="h-4 w-4" />
            Reports
          </TabsTrigger>
          <TabsTrigger value="bans" className="flex items-center gap-2">
            <Ban className="h-4 w-4" />
            Bans
          </TabsTrigger>
        </TabsList>
        
        <TabsContent value="reports" className="mt-6">
          <ReportsQueue />
        </TabsContent>
        
        <TabsContent value="bans" className="mt-6">
          <div className="grid gap-6 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <ActiveBans />
            </div>
            <div>
              <BanUserForm />
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
