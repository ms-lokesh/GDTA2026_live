# GDTA 2026 Conference Platform

A comprehensive conference management platform for the Global Design Thinking Alliance (GDTA) 2026 Conference. The platform combines a professional public-facing website with a powerful admin and registration system.

## 🌟 Platform Overview

This platform consists of two main components:

1. **Public Website** - Professional multi-page conference website
2. **Admin System** - Advanced registration and event management system

### Conference Details
- **Theme**: Chaos & Clarity
- **Date**: September 29-30, 2026
- **Host**: SNS Institutions
- **Location**: India

## 📂 Project Structure

```
GDTA2026/
├── admin_system/              # Admin & Registration System
│   ├── app.py                 # Flask application
│   ├── db/                    # Database models (Firebase)
│   ├── routes/                # API endpoints
│   ├── logic/                 # Business logic
│   ├── llm/                   # AI chatbot integration
│   ├── static/                # Frontend files
│   └── README.md              # Detailed admin system docs
│
├── css/                       # Website stylesheets
├── js/                        # Website JavaScript
├── img/                       # Images and assets
├── lib/                       # Third-party libraries
│
├── index.html                 # Homepage
├── about-gdta-2026.html       # About GDTA 2026
├── about-gdta.html            # About GDTA organization
├── about-sns.html             # About SNS Institutions
├── program-schedule.html      # Conference schedule
├── program-sessions.html      # Session details
├── program-safari.html        # Design safari information
├── organizing-team.html       # Team members
├── register.html              # Registration page
├── register-safari.html       # Safari registration
├── sponsors.html              # Sponsors
├── travel-stay.html           # Travel information
├── contact.html               # Contact page
├── hackathon.html             # Hackathon details
└── code.html                  # Code of conduct
```

## 🚀 Quick Start

### Public Website
Simply open `index.html` in a web browser or deploy to any web server.

### Admin System
See detailed instructions in `admin_system/README.md`

```bash
cd admin_system
pip install -r requirements.txt
python3 app.py
```

## 🎨 Website Features

### Design & Theme
- Modern dark theme (#1F1F1F, #2B2B2B)
- Gold accent colors (#F2B705)
- Smooth scroll animations (WOW.js)
- Fully responsive design
- Mobile-optimized navigation

### Navigation
- Multi-page structure with 14+ pages
- Dropdown menus for complex content
- Sticky navigation bar
- Breadcrumb navigation
- Quick links and social media integration

### Content Pages
- **Home**: Conference overview and highlights
- **About**: GDTA 2026, GDTA organization, SNS Institutions
- **Program**: Full schedule, session details, design safari
- **Registration**: Online form with dietary preferences
- **Team**: Organizing committee and advisors
- **Sponsors**: Partner organizations
- **Travel**: Accommodation and travel information
- **Contact**: Contact form and location map
- **Hackathon**: Hackathon competition details

## 🔧 Admin System Features

See `admin_system/README.md` for complete documentation.

### Key Capabilities
- Multi-event management
- Role-based access (Super Admin / Admin)
- Registration management with approval workflow
- QR code ID card generation
- Venue and volunteer management
- AI-powered chatbot
- Email system
- Data export
- Access logging

## 🛠️ Technology Stack

### Public Website
- **Frontend**: HTML5, CSS3, JavaScript (ES6)
- **Framework**: Bootstrap 5.0.0
- **Libraries**: jQuery 3.4.1, WOW.js, Animate.css
- **Icons**: Font Awesome 7.0.0, Bootstrap Icons
- **Fonts**: Google Fonts (Montserrat, Open Sans)

### Admin System
- **Backend**: Python 3.8+, Flask
- **Database**: Firebase Firestore
- **AI**: Google Gemini API
- **Authentication**: Session-based with role management
- **Email**: SMTP (Gmail)
- **Frontend**: Bootstrap 5, jQuery, DataTables

## 📱 Responsive Design

The website is fully responsive and optimized for:
- Desktop (1920px+)
- Laptop (1366px - 1920px)
- Tablet (768px - 1366px)
- Mobile (320px - 768px)

## Project Structure

```
GDTA2026/
│
├── css/
│   ├── bootstrap.min.css          # Bootstrap framework styles
│   ├── style.css                  # Main template stylesheet
│   └── custom-overrides.css       # GDTA theme color overrides
│
├── img/
│   ├── placeholder-hero.jpg       # Hero section background placeholder
│   ├── placeholder-section.jpg    # General section image placeholder
│   ├── placeholder-card.jpg       # Card image placeholder
│   └── placeholder-logo.png       # Logo placeholder
│
├── js/
│   └── main.js                    # Main JavaScript (smooth scroll disabled)
│
├── lib/
│   ├── animate/
│   │   ├── animate.css
│   │   └── animate.min.css
│   ├── easing/
│   │   ├── easing.js
│   │   └── easing.min.js
│   ├── lightbox/
│   ├── owlcarousel/
│   ├── waypoints/
│   │   └── waypoints.min.js
│   └── wow/
│       ├── wow.js
│       └── wow.min.js
│
├── index.html                     # Home page
├── about-gdta.html                # About GDTA organization
├── about-gdta-2026.html           # About GDTA 2026 conference
├── about-sns.html                 # About SNS Institutions (host)
├── program-schedule.html          # Conference schedule (2 days)
├── program-sessions.html          # Keynote speakers & sessions
├── program-safari.html            # Design safari details
├── travel-stay.html               # Travel & accommodation info
├── sponsors.html                  # Sponsors & partners
├── contact.html                   # Contact form
├── register.html                  # Conference registration
├── README.md                      # Project documentation
└── index_backup.html              # Original SNS AI Education backup
```

## Website Pages

### 1. Home Page (index.html)
- Hero section with conference title and dates
- Welcome message explaining "Chaos & Clarity" theme
- Key highlights cards (networking, learning, design safari)
- Call-to-action to registration

### 2. About Section
**About GDTA (about-gdta.html)**
- GDTA organization overview
- Mission and vision
- History and impact

**About GDTA 2026 (about-gdta-2026.html)**
- Conference theme: "Chaos & Clarity"
- Objectives and goals
- Expected outcomes
- Target audience

**About SNS Institutions (about-sns.html)**
- Venue information
- SNS Institutions background
- Facilities and location
- Why SNS as host

### 3. Program Section
**Schedule (program-schedule.html)**
- Day 1 (September 29, 2026) detailed schedule
- Day 2 (September 30, 2026) detailed schedule
- Session timings and topics

**Sessions & Speakers (program-sessions.html)**
- Keynote speaker profiles with placeholders
- Workshop descriptions
- Panel discussion details
- Session abstracts

**Design Safari (program-safari.html)**
- Experiential learning session
- Date: September 30, 10:00 AM - 12:00 PM
- Optional participation details
- What to expect

### 4. Travel & Stay (travel-stay.html)
- How to reach (by air, train, road)
- Accommodation options (premium, mid-range, budget)
- Local transportation information
- Nearby attractions

### 5. Sponsors (sponsors.html)
- Platinum sponsors showcase
- Gold sponsors showcase
- Partnership opportunities
- Sponsor benefits

### 6. Contact (contact.html)
- Conference email: conference@gdta.org
- Phone: +91 12345 67890
- Address: SNS Institutions, Coimbatore
- Contact form for inquiries
- Social media links

### 7. Register (register.html)
- Registration form with fields:
  - Full Name
  - Email Address
  - Phone Number
  - Organization
  - Designation
  - Design Safari Interest (Yes/No/Maybe)
  - Dietary Requirements
  - Terms & Conditions agreement
- Conference details sidebar (dates, venue, fees)

## Navigation Structure

**Main Menu:**
- Home (index.html)
- About (dropdown)
  - GDTA (about-gdta.html)
  - GDTA 2026 (about-gdta-2026.html)
  - SNS Institutions (about-sns.html)
- Program (dropdown)
  - Schedule (program-schedule.html)
  - Sessions (program-sessions.html)
  - Design Safari (program-safari.html)
- Travel & Stay (travel-stay.html)
- Sponsors (sponsors.html)
- Contact (contact.html)
- Register (register.html) - CTA button styled

## Theme & Design

**GDTA Color Palette:**
- Primary Background: #1F1F1F (Dark charcoal)
- Card Background: #2B2B2B (Lighter dark gray)
- Accent Color: #F2B705 (Gold)
- Text Primary: #FFFFFF (White)
- Text Secondary: #D1D1D1 (Light gray)
- Text Muted: #9CA3AF (Muted gray)
**Animation System:**
- WOW.js for scroll-triggered animations
- Animate.css for animation effects
- Staggered delays for sequential element animations
- FadeIn variants (fadeInLeft, fadeInRight, fadeInUp, fadeInDown)

**Typography:**
- Montserrat (headings and bold text)
- Open Sans (body text)
- Responsive font sizes across devices

## Design Features

### Visual Effects
- Dark theme with high contrast
- Gold accent colors for CTAs and highlights
- Card shadows for depth perception
- Smooth transitions on hover states
- WOW.js scroll animations throughout

### Responsive Design
- Mobile-first Bootstrap 5 grid system
- Adaptive layouts for all screen sizes
- Collapsible navigation menu on mobile
- Touch-friendly interface elements
- Optimized for desktop, tablet, and mobile

### Navigation Features
- Fixed top navbar with transparency
- Dropdown menus for About and Program sections
- Active page highlighting
- Mobile-responsive hamburger menu
- Consistent navigation across all 11 pages

## Setup and Installation

### Prerequisites
- Modern web browser (Chrome, Firefox, Safari, Edge)
- Local web server (optional for development)
- Git (for version control)

### Installation Steps

1. Clone the repository:
```bash
git clone https://github.com/yourusername/GDTA2026.git
cd GDTA2026
```

2. Open the project:
   - Simply open `index.html` in a web browser, or
   - Use a local development server (recommended)

3. For local development server (Python):
```bash
python -m http.server 8000
```
Then navigate to `http://localhost:8000`

4. For local development server (Node.js):
```bash
npx http-server -p 8000
```
Then navigate to `http://localhost:8000`

## Development Workflow

### File Modification Guidelines

**HTML (index.html)**
- Main structure and content
- Modal forms and popups
- Section organization

**CSS (custom-overrides.css)**
- Color customizations
- Typography overrides
- Custom component styling

**CSS (style.css)**
- Template base styles
- Layout structures
- Responsive breakpoints

### Making Changes

**Content Updates:**
1. Edit page content in respective HTML files
2. Update conference details in registration form
3. Modify schedule in program-schedule.html
4. Add speaker information in program-sessions.html

**Style Customizations:**
1. Theme colors in `css/custom-overrides.css`
2. Component styling overrides
3. Custom animations and effects
4. Typography adjustments

**Navigation Updates:**
1. Update navbar links in all pages consistently
2. Ensure active states reflect current page
3. Test dropdown menus on all devices

**Testing:**
1. Test all pages across devices
2. Verify form submissions
3. Check animation triggers
4. Validate responsive breakpoints
5. Test navigation on mobile

## Browser Compatibility

- Google Chrome (latest)
- Mozilla Firefox (latest)
- Safari (latest)
- Microsoft Edge (latest)
- Mobile browsers (iOS Safari, Chrome Mobile)

## Conference Information

### Event Details
- **Name:** GDTA 2026 Conference
- **Theme:** Chaos & Clarity
- **Dates:** September 29-30, 2026
- **Venue:** SNS Institutions, Coimbatore, Tamil Nadu, India
- **Registration Fee:** ₹2,500 per participant

### Key Features
- 2-day conference with expert keynotes
- Interactive workshops and panel discussions
- Design Safari experiential learning session
- Networking opportunities with design thinking practitioners
- Certificate of participation

## Social Media Integration

- Instagram: https://www.instagram.com/gdtaconference
- YouTube: https://youtube.com/@gdtaofficial
- LinkedIn: https://www.linkedin.com/company/gdta/

## Deployment

The website can be deployed via GitHub Pages, Netlify, Vercel, or any static hosting service.

### Deployment Steps (GitHub Pages)
1. Commit all changes to main branch
2. Push to GitHub repository
3. Configure GitHub Pages in repository settings
4. Select main branch and root directory
5. Access via provided GitHub Pages URL

### Deployment Steps (Netlify/Vercel)
1. Connect your repository
2. Set build command: none (static site)
3. Set publish directory: / (root)
4. Deploy automatically on push

## Version History

### Version 2.0 (Current - GDTA 2026)
- Multi-page website structure (11 pages)
- GDTA Conference theme "Chaos & Clarity"
- Dark theme with gold accents
- Dropdown navigation menus
- Registration form with design safari option
- Comprehensive conference information
- Placeholder images for all sections

### Version 1.0 (Original - SNS AI Education)
- Single-page design with 3D hero section
- Three AI/ML program showcases
- Enrollment modal form
- Light theme with teal accents

## Credits

### Template Base
- Original Template: Bootstrap-based responsive template
- Heavily customized for GDTA Conference

### Organizations
- Global Design Thinking Alliance (GDTA)
- SNS Institutions (Host Venue)

### Libraries & Frameworks
- Bootstrap 5.0.0
- WOW.js, Animate.css
- jQuery 3.4.1
- Font Awesome 7.0.0
- Google Fonts

## License

This project is for the GDTA 2026 Conference. All rights reserved.

## Contact Information

**Conference Inquiries:**
- Email: conference@gdta.org
- Phone: +91 12345 67890
- Address: SNS Institutions, Coimbatore, Tamil Nadu, India

**Social Media:**
- Instagram: @gdtaconference
- YouTube: @gdtaofficial
- LinkedIn: /company/gdta

## Maintenance and Updates

### Regular Updates
- Update speaker information as confirmed
- Replace placeholder images with actual photos
- Update schedule timings as finalized
- Monitor and respond to contact form submissions
- Update sponsor logos as partnerships confirmed

### Future Enhancements
- Backend integration for registration form processing
- Payment gateway integration for registration fees
- Email confirmation system for registrations
- Analytics tracking for visitor insights
- Live schedule updates during conference
- Photo gallery post-conference
- Testimonials and feedback section

## Technical Notes

### Image Placeholders
Currently using placeholder images. Replace with actual images:
- `placeholder-hero.jpg` - Conference venue or keynote images
- `placeholder-section.jpg` - General section backgrounds
- `placeholder-card.jpg` - Speaker photos, venue images
- `placeholder-logo.png` - GDTA logo, sponsor logos

### Form Submission
Registration and contact forms currently have no backend. Integrate with:
- Backend API endpoint
- Google Forms
- Email service (SendGrid, Mailchimp)
- Form submission service (Formspree, Netlify Forms)

### Performance Optimization
- Compress and optimize actual images before upload
- Enable browser caching
- Minify CSS and JavaScript for production
- Use CDN for library files
- Implement lazy loading for images

---

**Built for GDTA 2026 Conference - "Chaos & Clarity"**

- Testimonials section
- Alumni success stories

---

**Last Updated:** January 2026  
**Maintained by:** SNS Institutions Development Team