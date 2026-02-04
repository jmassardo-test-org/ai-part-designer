/**
 * Marketplace and community feature types.
 * 
 * Types for marketplace browsing, lists, saves, and starters.
 */

// =============================================================================
// Category & Tag Types
// =============================================================================

export interface CategoryResponse {
  name: string;
  slug: string;
  design_count: number;
}

export interface TagResponse {
  name: string;
  count: number;
}

// =============================================================================
// Design List Types
// =============================================================================

export interface DesignList {
  id: string;
  name: string;
  description: string | null;
  icon: string;
  color: string;
  is_public: boolean;
  position: number;
  item_count: number;
  created_at: string;
  updated_at: string;
}

export interface ListCreate {
  name: string;
  description?: string;
  icon?: string;
  color?: string;
  is_public?: boolean;
}

export interface ListUpdate {
  name?: string;
  description?: string;
  icon?: string;
  color?: string;
  is_public?: boolean;
  position?: number;
}

// =============================================================================
// List Item Types
// =============================================================================

export interface ListItem {
  id: string;
  list_id: string;
  design_id: string;
  note: string | null;
  position: number;
  created_at: string;
  design_name?: string;
  design_thumbnail_url?: string;
}

export interface ListItemWithDesign extends ListItem {
  design: DesignSummary;
}

export interface AddToListRequest {
  design_id: string;
  note?: string;
}

// =============================================================================
// Design Save Types
// =============================================================================

export interface SaveResponse {
  design_id: string;
  saved_at: string;
  lists: DesignList[];
}

export interface UnsaveResponse {
  design_id: string;
  removed_from_lists: number;
}

export interface SaveStatusResponse {
  design_id: string;
  is_saved: boolean;
  in_lists: string[];
}

// =============================================================================
// Marketplace Design Types
// =============================================================================

export interface DesignSummary {
  id: string;
  name: string;
  description: string | null;
  thumbnail_url: string | null;
  category: string | null;
  tags: string[];
  save_count: number;
  remix_count: number;
  is_starter: boolean;
  created_at: string;
  published_at: string | null;
  author_id: string;
  author_name: string;
}

export interface MarketplaceDesign extends DesignSummary {
  is_saved: boolean;
  in_lists: string[];
  remixed_from_id: string | null;
  remixed_from_name: string | null;
  featured_at: string | null;
  has_step: boolean;
  has_stl: boolean;
}

export interface PaginatedDesigns {
  items: DesignSummary[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface PaginatedSaves {
  items: ListItemWithDesign[];
  total: number;
  page: number;
  page_size: number;
}

// =============================================================================
// Publish Types
// =============================================================================

export interface PublishDesignRequest {
  category?: string;
  tags?: string[];
  is_starter?: boolean;
}

export interface PublishDesignResponse {
  id: string;
  published_at: string;
  category: string | null;
  is_starter: boolean;
}

// =============================================================================
// Starter Design Types
// =============================================================================

export interface StarterDesign {
  id: string;
  name: string;
  description: string | null;
  thumbnail_url: string | null;
  category: string | null;
  tags: string[];
  remix_count: number;
  exterior_dimensions: {
    width: number;
    depth: number;
    height: number;
    unit: string;
  } | null;
  features: string[];
  created_at: string;
}

export interface StarterDetail extends StarterDesign {
  enclosure_spec: Record<string, unknown> | null;
  author_id: string;
  author_name: string;
}

export interface PaginatedStarters {
  items: StarterDesign[];
  total: number;
  page: number;
  page_size: number;
}

export interface RemixResponse {
  id: string;
  name: string;
  remixed_from_id: string;
  remixed_from_name: string;
  enclosure_spec: Record<string, unknown>;
  created_at: string;
}

// =============================================================================
// Browse Filter Types
// =============================================================================

export interface BrowseFilters {
  category?: string;
  tags?: string[];
  search?: string;
  sort?: 'popular' | 'recent' | 'trending' | 'saves';
  page?: number;
  page_size?: number;
}
