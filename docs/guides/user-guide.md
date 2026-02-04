# AI Part Designer - User Guide

Welcome to AI Part Designer! This guide will help you get started with creating custom 3D-printable enclosures and parts using AI-powered design generation.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Creating Your First Design](#creating-your-first-design)
3. [Using Templates](#using-templates)
4. [Chat Commands](#chat-commands)
5. [Design Management](#design-management)
6. [Exporting Designs](#exporting-designs)
7. [Account & Settings](#account--settings)
8. [Keyboard Shortcuts](#keyboard-shortcuts)
9. [FAQ](#faq)
10. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Creating an Account

1. Visit [AI Part Designer](https://aipartdesigner.com)
2. Click **Sign Up** in the top right
3. Choose your preferred method:
   - **Email & Password** - Enter your details and create a password
   - **Google** - Sign in with your Google account
   - **GitHub** - Sign in with your GitHub account
4. Verify your email address (if using email signup)
5. Complete the quick onboarding tour

### Your Dashboard

After logging in, you'll see your **Dashboard** with:

- **Recent Designs** - Your latest creations
- **Quick Actions** - Start a new design or browse templates
- **Usage Stats** - Your current plan usage

---

## Creating Your First Design

### Using the Chat Interface

1. Click **Chat** in the navigation bar
2. Describe what you want to create in natural language:
   ```
   Create a 100mm x 60mm enclosure for a Raspberry Pi 4 
   with ventilation holes and a snap-fit lid
   ```
3. Wait for the AI to generate your design (usually 30-60 seconds)
4. View the 3D preview and adjust as needed
5. Click **Save to Library** to keep your design

### Tips for Better Results

| Do | Don't |
|---|---|
| Include specific dimensions | Use vague terms like "small" or "big" |
| Mention the component you're housing | Assume the AI knows your use case |
| Specify mounting requirements | Forget about screw holes |
| Request ventilation if needed | Over-constrain your design |

### Example Prompts

**Electronics Enclosure:**
```
Design an enclosure for an Arduino Uno with:
- Wall thickness of 2.5mm
- Ventilation slots on the sides
- Access for USB and power ports
- M3 mounting holes in the corners
```

**Mounting Bracket:**
```
Create an L-bracket to mount a camera module at a 45-degree angle.
The bracket should have:
- 4mm thickness for rigidity
- Mounting holes for M4 screws
- 50mm arm length on each side
```

---

## Using Templates

Templates are pre-built designs that you can customize for your needs.

### Browsing Templates

1. Click **Templates** in the navigation
2. Browse by category or search for specific items
3. Click on a template to see details and preview

### Customizing a Template

1. Select a template
2. Click **Use Template**
3. Modify the parameters:
   - Dimensions
   - Wall thickness
   - Hole positions
   - Features
4. Click **Generate** to create your customized version

### Saving as Template

Turn your own designs into reusable templates:

1. Open a design you want to save as a template
2. Click **Actions** → **Save as Template**
3. Add a name, description, and category
4. Define customizable parameters
5. Click **Save**

---

## Chat Commands

Use slash commands for quick actions in the chat:

### Navigation Commands

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/clear` | Clear the current conversation |
| `/new` | Start a new design conversation |

### Design Commands

| Command | Description |
|---------|-------------|
| `/dimension <name> <value>` | Set a dimension (e.g., `/dimension width 100mm`) |
| `/export <format>` | Export current design (STEP, STL, OBJ) |
| `/template <name>` | Load a template |
| `/history` | Show conversation history |

### Generation Commands

| Command | Description |
|---------|-------------|
| `/generate` | Force regeneration of current design |
| `/refine <instruction>` | Refine the current design |
| `/undo` | Undo last change |

---

## Design Management

### Viewing Your Designs

1. Click **Designs** in the navigation
2. View all your saved designs
3. Use filters to find specific designs:
   - Search by name
   - Filter by category
   - Sort by date or name

### Organizing Designs

**Create Projects:**
1. Click **Projects** → **New Project**
2. Add a name and description
3. Add designs to your project

**Add Tags:**
1. Open a design
2. Click **Edit Tags**
3. Add relevant tags for easy searching

### Version History

Each design keeps a history of changes:

1. Open a design
2. Click **History** tab
3. View previous versions
4. Restore any previous version

---

## Exporting Designs

### Supported Formats

| Format | Best For |
|--------|----------|
| **STEP** | CAD software, manufacturing |
| **STL** | 3D printing |
| **OBJ** | 3D visualization, rendering |
| **GLTF** | Web applications, AR/VR |

### How to Export

1. Open your design
2. Click **Export** button
3. Choose your format
4. Adjust export settings if needed
5. Click **Download**

### Batch Export

Export multiple designs at once:

1. Go to **Designs**
2. Select multiple designs (checkbox)
3. Click **Actions** → **Export Selected**
4. Choose format and download

---

## Account & Settings

### Managing Your Profile

1. Click your avatar → **Settings**
2. Update your:
   - Display name
   - Email address
   - Profile picture

### Connected Accounts

Link social accounts for easier login:

1. Go to **Settings** → **Account**
2. Click **Connect Google** or **Connect GitHub**
3. Authorize the connection

### Subscription & Billing

**View Your Plan:**
1. Go to **Settings** → **Billing**
2. See your current plan and usage

**Upgrade Your Plan:**
1. Click **Upgrade**
2. Choose Pro or Enterprise
3. Complete checkout via Stripe

**Manage Billing:**
- Update payment method
- View invoices
- Cancel subscription

### Theme Settings

Switch between light and dark mode:

1. Click the theme toggle (sun/moon icon) in the navbar
2. Choose **Light**, **Dark**, or **System**

---

## Keyboard Shortcuts

Navigate faster with keyboard shortcuts:

### Global Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+K` | Quick search |
| `Ctrl+H` | Toggle history panel |
| `Ctrl+N` | New design |
| `?` | Show shortcuts help |
| `Escape` | Close modal/panel |

### Design View Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+S` | Save design |
| `Ctrl+E` | Export design |
| `Ctrl+Z` | Undo |
| `Ctrl+Shift+Z` | Redo |

### 3D Viewer Shortcuts

| Shortcut | Action |
|----------|--------|
| `R` | Reset view |
| `F` | Focus on model |
| `G` | Toggle grid |
| `W` | Wireframe mode |

---

## FAQ

### General Questions

**Q: What file formats can I upload?**
A: We support STEP, STL, OBJ for 3D models, and PDF, PNG, JPG for datasheets.

**Q: How accurate are the generated dimensions?**
A: Dimensions are accurate to 0.1mm. Always verify critical dimensions before manufacturing.

**Q: Can I use the designs commercially?**
A: Yes! All designs you create are yours to use commercially.

### Account Questions

**Q: How do I change my password?**
A: Go to Settings → Security → Change Password.

**Q: Can I delete my account?**
A: Yes, go to Settings → Account → Delete Account. This is permanent.

**Q: How do I update my payment method?**
A: Go to Settings → Billing → Manage Billing to update your card.

### Design Questions

**Q: Why is my generation taking so long?**
A: Complex designs with many features take longer. Typical generation time is 30-60 seconds.

**Q: Can I edit the generated CAD directly?**
A: Export to STEP and edit in your preferred CAD software like Fusion 360, SolidWorks, or FreeCAD.

**Q: How do I add threads to a hole?**
A: Include "M3 threaded hole" or "1/4-20 tapped hole" in your prompt.

---

## Troubleshooting

### Common Issues

**Design generation fails:**
- Check your internet connection
- Try simplifying your prompt
- Contact support if issue persists

**Can't log in:**
- Reset your password
- Clear browser cookies
- Try a different browser

**Export not working:**
- Disable browser popup blocker
- Try a different export format
- Check your storage quota

**3D viewer not loading:**
- Enable WebGL in your browser
- Update your graphics drivers
- Try a different browser

### Getting Help

- **Email:** support@aipartdesigner.com
- **Discord:** [Join our community](https://discord.gg/aipartdesigner)
- **Documentation:** [docs.aipartdesigner.com](https://docs.aipartdesigner.com)

---

## Next Steps

Ready to create your first design? Here are some ideas:

1. 🎯 **Start simple** - Create a basic box with a lid
2. 📦 **Use templates** - Customize a pre-built enclosure
3. 🔧 **Get specific** - Add mounting holes and ventilation
4. 🎨 **Experiment** - Try different styles and features

Happy designing! 🚀
