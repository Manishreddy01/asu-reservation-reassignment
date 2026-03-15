import { Link } from 'react-router-dom';
import Navbar from '../components/Navbar';
import { useAuth } from '../context/AuthContext';
import './LandingPage.css';

export default function LandingPage() {
  const { user } = useAuth();
  const appPath     = user ? '/app'         : '/login';
  const libraryPath = user ? '/app/library' : '/login';

  return (
    <div className="landing">
      <Navbar />

      <HeroSection   appPath={appPath} />
      <ServicesSection appPath={appPath} libraryPath={libraryPath} />
      <HowItWorksSection />
      <BenefitsSection />
      <LandingFooter />
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────
   Hero
───────────────────────────────────────────────────────────────── */
function HeroSection({ appPath }) {
  return (
    <section className="hero">
      <div className="hero-inner">
        <div className="hero-content">
          <div className="hero-eyebrow">Arizona State University</div>
          <h1 className="hero-headline">
            Reserve Smarter.<br />Show Up Better.
          </h1>
          <p className="hero-subtext">
            Book study rooms and recreation courts at ASU facilities.
            Location-verified check-in keeps reservations fair — unused
            slots are automatically freed for students who actually show up.
          </p>
          <div className="hero-actions">
            <Link to={appPath} className="hero-btn-primary">
              Get Started
            </Link>
            <a href="#how-it-works" className="hero-btn-outline">
              How It Works
            </a>
          </div>
        </div>

        <div className="hero-visual" aria-hidden="true">
          <HeroIllustration />
        </div>
      </div>
    </section>
  );
}

/* ─────────────────────────────────────────────────────────────────
   Services
───────────────────────────────────────────────────────────────── */
function ServicesSection({ appPath, libraryPath }) {
  return (
    <section className="services">
      <div className="section-inner">
        <div className="section-label">Campus Resources</div>
        <h2 className="section-title">What Can You Reserve?</h2>
        <p className="section-subtitle">
          Two types of resources are available for booking through this system.
        </p>

        <div className="service-cards">
          <ServiceCard
            icon={<LibraryIcon />}
            accent="maroon"
            title="Library Study Rooms"
            location="Hayden Library"
            description="Reserve quiet, equipped study rooms for individual or group sessions. Rooms come with whiteboards, TV screens, and HDMI connections."
            features={['4 rooms available', 'Capacity 2–8 people', 'Equipment included']}
            appPath={libraryPath}
            label="Reserve a Study Room"
          />
          <ServiceCard
            icon={<CourtIcon />}
            accent="gold"
            title="Recreation Courts"
            location="SDFC Recreation Center"
            description="Book badminton courts at the Sun Devil Fitness Complex. Nets and shuttlecocks are provided on site."
            features={['4 courts available', 'Capacity up to 4 players', 'Equipment provided']}
            appPath={appPath}
            label="Reserve a Court"
          />
        </div>
      </div>
    </section>
  );
}

function ServiceCard({ icon, accent, title, location, description, features, appPath, label }) {
  return (
    <div className={`service-card service-card--${accent}`}>
      <div className="service-card-icon">{icon}</div>
      <div className="service-card-location">{location}</div>
      <h3 className="service-card-title">{title}</h3>
      <p className="service-card-desc">{description}</p>
      <ul className="service-card-features">
        {features.map(f => (
          <li key={f}>
            <CheckIcon /> {f}
          </li>
        ))}
      </ul>
      <Link to={appPath} className={`service-card-btn service-card-btn--${accent}`}>
        {label}
      </Link>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────
   How It Works
───────────────────────────────────────────────────────────────── */
function HowItWorksSection() {
  const steps = [
    {
      num: '01',
      title: 'Reserve',
      desc: 'Browse available rooms or courts and select a 1-hour time slot. Bookings are confirmed instantly.',
    },
    {
      num: '02',
      title: 'Check In',
      desc: 'Arrive at the building and tap Check In. Your device location is verified — no location, no check-in.',
    },
    {
      num: '03',
      title: 'Waitlist',
      desc: "If your preferred slot is full, join the waitlist. You'll be notified the moment a spot opens up.",
    },
    {
      num: '04',
      title: 'Reassignment',
      desc: "No-shows are released automatically after 15 minutes. The next waitlisted student gets 5 minutes to claim it.",
    },
  ];

  return (
    <section className="how-it-works" id="how-it-works">
      <div className="section-inner">
        <div className="section-label">The Process</div>
        <h2 className="section-title">How It Works</h2>
        <p className="section-subtitle">
          Four simple steps from booking to using your reservation.
        </p>

        <div className="steps-grid">
          {steps.map((step, i) => (
            <div className="step-card" key={step.num}>
              <div className="step-num">{step.num}</div>
              <h3 className="step-title">{step.title}</h3>
              <p className="step-desc">{step.desc}</p>
              {i < steps.length - 1 && (
                <div className="step-arrow" aria-hidden="true">›</div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ─────────────────────────────────────────────────────────────────
   Benefits
───────────────────────────────────────────────────────────────── */
function BenefitsSection() {
  const benefits = [
    {
      icon: <BenefitIconCalendar />,
      title: 'Less Waste',
      desc: 'No-show reservations are detected and released automatically, so rooms and courts are never left empty needlessly.',
    },
    {
      icon: <BenefitIconLocation />,
      title: 'Verified Presence',
      desc: "Check-in requires you to be physically near the building. Your reservation is only confirmed when you're actually there.",
    },
    {
      icon: <BenefitIconQueue />,
      title: 'Fair Access',
      desc: 'The waitlist is first-come, first-served. When a slot opens, the next student in line gets an instant offer.',
    },
  ];

  return (
    <section className="benefits">
      <div className="section-inner">
        <div className="section-label">Why It Matters</div>
        <h2 className="section-title">Designed for Fairness</h2>
        <p className="section-subtitle">
          Built to help every ASU student get fair access to shared campus resources.
        </p>

        <div className="benefits-grid">
          {benefits.map(b => (
            <div className="benefit-card" key={b.title}>
              <div className="benefit-icon">{b.icon}</div>
              <h3 className="benefit-title">{b.title}</h3>
              <p className="benefit-desc">{b.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ─────────────────────────────────────────────────────────────────
   Footer
───────────────────────────────────────────────────────────────── */
function LandingFooter() {
  return (
    <footer className="landing-footer">
      <div className="landing-footer-inner">
        <div className="landing-footer-logo">
          <ForkIconSmall />
          <span>ASU Campus Reservations</span>
        </div>
        <p className="landing-footer-note">
          Prototype system &mdash; Arizona State University &mdash; Not for production use.
        </p>
      </div>
    </footer>
  );
}

/* ─────────────────────────────────────────────────────────────────
   SVG icons (inline, no external dependency)
───────────────────────────────────────────────────────────────── */

function HeroIllustration() {
  return (
    <div className="hero-illustration">
      <div className="hi-card hi-card--1">
        <div className="hi-card-bar" />
        <div className="hi-card-line" />
        <div className="hi-card-line hi-card-line--short" />
        <div className="hi-card-tag">Study Room A101</div>
        <div className="hi-card-badge hi-badge--active">Active</div>
      </div>
      <div className="hi-card hi-card--2">
        <div className="hi-card-bar hi-card-bar--gold" />
        <div className="hi-card-line" />
        <div className="hi-card-line hi-card-line--short" />
        <div className="hi-card-tag">Badminton Court 1</div>
        <div className="hi-card-badge hi-badge--reserved">Reserved</div>
      </div>
      <div className="hi-checkin">
        <CheckInIcon />
        <span>Checked In</span>
      </div>
    </div>
  );
}

function LibraryIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" width="32" height="32">
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
      <line x1="9" y1="7" x2="15" y2="7" />
      <line x1="9" y1="11" x2="15" y2="11" />
    </svg>
  );
}

function CourtIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" width="32" height="32">
      <rect x="2" y="5" width="20" height="14" rx="2" />
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="2" y1="12" x2="22" y2="12" />
      <circle cx="6" cy="8" r="1" fill="currentColor" stroke="none" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="currentColor" width="14" height="14" aria-hidden="true">
      <path fillRule="evenodd" d="M13.78 4.22a.75.75 0 010 1.06l-7.25 7.25a.75.75 0 01-1.06 0L2.22 9.28a.75.75 0 011.06-1.06L6 10.94l6.72-6.72a.75.75 0 011.06 0z" />
    </svg>
  );
}

function CheckInIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" width="20" height="20">
      <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z" />
      <circle cx="12" cy="9" r="2.5" />
    </svg>
  );
}

function BenefitIconCalendar() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" width="28" height="28">
      <rect x="3" y="4" width="18" height="18" rx="2" />
      <line x1="16" y1="2" x2="16" y2="6" />
      <line x1="8" y1="2" x2="8" y2="6" />
      <line x1="3" y1="10" x2="21" y2="10" />
      <polyline points="9 16 11 18 15 14" />
    </svg>
  );
}

function BenefitIconLocation() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" width="28" height="28">
      <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z" />
      <circle cx="12" cy="9" r="2.5" />
    </svg>
  );
}

function BenefitIconQueue() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" width="28" height="28">
      <line x1="8" y1="6" x2="21" y2="6" />
      <line x1="8" y1="12" x2="21" y2="12" />
      <line x1="8" y1="18" x2="21" y2="18" />
      <circle cx="3" cy="6" r="1.5" fill="currentColor" stroke="none" />
      <circle cx="3" cy="12" r="1.5" fill="currentColor" stroke="none" />
      <circle cx="3" cy="18" r="1.5" fill="currentColor" stroke="none" />
    </svg>
  );
}

function ForkIconSmall() {
  return (
    <svg viewBox="0 0 32 36" fill="none" aria-hidden="true" width="16" height="18">
      <rect x="14" y="0"  width="4" height="36" rx="2" fill="currentColor" />
      <rect x="5"  y="0"  width="3" height="20" rx="1.5" fill="currentColor" />
      <rect x="24" y="0"  width="3" height="20" rx="1.5" fill="currentColor" />
      <rect x="5"  y="17" width="4" height="4"  rx="1" fill="currentColor" />
      <rect x="23" y="17" width="4" height="4"  rx="1" fill="currentColor" />
    </svg>
  );
}
