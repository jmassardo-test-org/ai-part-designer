/**
 * Understanding summary sidebar showing current AI understanding.
 */

import { 
  Box, 
  Ruler, 
  Settings2, 
  AlertTriangle,
} from 'lucide-react';
import { useMemo } from 'react';
import type { PartUnderstanding } from '@/lib/conversations';

interface UnderstandingSidebarProps {
  understanding: PartUnderstanding | null | undefined;
}

export function UnderstandingSidebar({ understanding }: UnderstandingSidebarProps) {
  const completenessPercent = understanding ? Math.round(understanding.completeness_score * 100) : 0;
  const completenessColor = useMemo(() => {
    if (completenessPercent >= 70) return 'text-green-600 dark:text-green-400 bg-green-100 dark:bg-green-900/50';
    if (completenessPercent >= 40) return 'text-amber-600 dark:text-amber-400 bg-amber-100 dark:bg-amber-900/50';
    return 'text-red-600 dark:text-red-400 bg-red-100 dark:bg-red-900/50';
  }, [completenessPercent]);

  if (!understanding) {
    return (
      <div className="p-3 text-center text-gray-500 dark:text-gray-400">
        <p className="text-xs">Waiting for input...</p>
      </div>
    );
  }
  
  const dimensions = Object.entries(understanding.dimensions || {});
  const features = understanding.features || [];
  const missing = understanding.missing_critical || [];

  return (
    <div className="p-3 text-xs">
      {/* Header row: Part Type + Completeness */}
      <div className="flex items-center justify-between gap-4 mb-2">
        {/* Classification */}
        {understanding.classification && (
          <div className="flex items-center gap-1.5">
            <Box className="w-3.5 h-3.5 text-gray-500 dark:text-gray-400" />
            <span className="font-medium text-gray-900 dark:text-gray-100 capitalize">
              {understanding.classification.category}
              {understanding.classification.subcategory && (
                <span className="text-gray-500 dark:text-gray-400 font-normal"> ({understanding.classification.subcategory})</span>
              )}
            </span>
          </div>
        )}
        
        {/* Completeness */}
        <div className="flex items-center gap-2">
          <div className="w-16 h-1.5 bg-gray-200 dark:bg-gray-600 rounded-full overflow-hidden">
            <div 
              className={`h-full transition-all ${completenessPercent >= 70 ? 'bg-green-500' : completenessPercent >= 40 ? 'bg-amber-500' : 'bg-red-500'}`}
              style={{ width: `${completenessPercent}%` }}
            />
          </div>
          <span className={`text-[10px] px-1.5 py-0.5 rounded ${completenessColor}`}>
            {completenessPercent}%
          </span>
        </div>
      </div>
      
      {/* Dimensions + Features in columns */}
      <div className="flex gap-4">
        {/* Dimensions */}
        {dimensions.length > 0 && (
          <div className="flex-1 min-w-0">
            <h4 className="font-medium text-gray-700 dark:text-gray-300 flex items-center gap-1 mb-1">
              <Ruler className="w-3 h-3" />
              Dimensions
            </h4>
            <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 text-gray-600 dark:text-gray-300">
              {dimensions.slice(0, 6).map(([key, dim]) => (
                <div key={key} className="flex justify-between truncate">
                  <span className="truncate">{dim.name.replace(/_/g, ' ')}</span>
                  <span className="font-mono ml-1">
                    {dim.value}{dim.unit}
                    {dim.source === 'inferred' && <span className="text-amber-500 dark:text-amber-400">*</span>}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
        
        {/* Features + Missing */}
        <div className="flex-1 min-w-0">
          {features.length > 0 && (
            <div className="mb-2">
              <h4 className="font-medium text-gray-700 dark:text-gray-300 flex items-center gap-1 mb-1">
                <Settings2 className="w-3 h-3" />
                Features
              </h4>
              <div className="text-gray-600 dark:text-gray-300 space-y-0.5">
                {features.slice(0, 3).map((feature, index) => (
                  <div key={index} className="truncate">
                    {feature.feature_type}{feature.count > 1 && ` ×${feature.count}`}
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {missing.length > 0 && (
            <div>
              <h4 className="font-medium text-amber-700 dark:text-amber-400 flex items-center gap-1 mb-1">
                <AlertTriangle className="w-3 h-3" />
                Missing
              </h4>
              <div className="text-amber-600 dark:text-amber-300 space-y-0.5">
                {missing.slice(0, 3).map((item, index) => (
                  <div key={index} className="truncate">
                    {item.replace(/_/g, ' ')}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
