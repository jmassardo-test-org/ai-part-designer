# ADR-001: Frontend Framework Selection

## Status
Proposed

## Context
We need to select a frontend framework for the AI Part Designer web application. The application requires:
- Complex interactive UI with 3D model visualization
- Real-time updates for job status and queue position
- Responsive design for desktop and tablet users
- Form-heavy interfaces for design customization
- Dashboard with data visualization
- Strong ecosystem for component libraries

## Decision
We will use **React 18+** with **TypeScript** as our frontend framework.

Supporting technology choices:
- **Build Tool**: Vite (fast development, optimized production builds)
- **State Management**: Zustand (lightweight, TypeScript-friendly)
- **UI Components**: shadcn/ui (customizable, accessible components)
- **3D Visualization**: Three.js with React Three Fiber
- **Forms**: React Hook Form with Zod validation
- **API Client**: TanStack Query (React Query)
- **Styling**: Tailwind CSS

## Consequences

### Positive
- **Large ecosystem**: Extensive libraries for 3D, forms, state management
- **Strong TypeScript support**: Better developer experience, fewer runtime errors
- **Hiring pool**: Largest talent pool of all frontend frameworks
- **Three.js integration**: React Three Fiber provides excellent 3D support
- **Community resources**: Abundant tutorials, Stack Overflow answers, etc.
- **Vite performance**: Sub-second HMR, fast builds

### Negative
- **Bundle size**: React + libraries can result in larger bundles (mitigated by code splitting)
- **Boilerplate**: More setup required compared to opinionated frameworks
- **Decision fatigue**: Many choices for state management, routing, etc.

### Neutral
- React 18's concurrent features may not be fully utilized initially
- Server components (Next.js) considered but SPA preferred for this use case

## Options Considered

| Framework | Pros | Cons | Score |
|-----------|------|------|-------|
| **React** | Largest ecosystem, best 3D support, TypeScript excellent | Bundle size, many choices | ⭐⭐⭐⭐⭐ |
| Vue 3 | Great DX, smaller bundle, good TypeScript | Smaller 3D ecosystem | ⭐⭐⭐⭐ |
| Angular | Enterprise-ready, opinionated, full-featured | Heavy, steep learning curve, less 3D support | ⭐⭐⭐ |
| Svelte | Smallest bundle, simple syntax | Smallest ecosystem, 3D support limited | ⭐⭐⭐ |
| SolidJS | Excellent performance | Very small ecosystem | ⭐⭐ |

## Technical Details

### Project Structure
```
frontend/
├── src/
│   ├── components/
│   │   ├── ui/           # shadcn components
│   │   ├── design/       # Design editor components
│   │   ├── viewer/       # 3D viewer components
│   │   └── dashboard/    # Dashboard components
│   ├── features/
│   │   ├── auth/
│   │   ├── designs/
│   │   ├── templates/
│   │   └── jobs/
│   ├── hooks/
│   ├── lib/
│   ├── stores/
│   └── types/
├── public/
└── tests/
```

### Key Dependencies
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "@tanstack/react-query": "^5.0.0",
    "zustand": "^4.4.0",
    "react-hook-form": "^7.48.0",
    "zod": "^3.22.0",
    "@react-three/fiber": "^8.15.0",
    "@react-three/drei": "^9.88.0",
    "three": "^0.158.0",
    "tailwindcss": "^3.3.0"
  }
}
```

## References
- [React Documentation](https://react.dev/)
- [Vite Documentation](https://vitejs.dev/)
- [React Three Fiber](https://docs.pmnd.rs/react-three-fiber)
- [shadcn/ui](https://ui.shadcn.com/)
- [TanStack Query](https://tanstack.com/query)
