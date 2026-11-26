import React from 'react';
import LandingNavbar from '../components/landing/LandingNavbar';
import HeroSection from '../components/landing/HeroSection';
import ProblemSolutionSection from '../components/landing/ProblemSolutionSection';
import AgentArchitectureSection from '../components/landing/AgentArchitectureSection';
import HowItWorksSection from '../components/landing/HowItWorksSection';
import FeaturesSection from '../components/landing/FeaturesSection';
import PlatformPreviewSection from '../components/landing/PlatformPreviewSection';
import FinalCTAAndFooter from '../components/landing/FinalCTAAndFooter';

export default function Landing() {
  return (
    <div className="min-h-screen bg-white text-slate-900 font-sans antialiased selection:bg-indigo-500 selection:text-white">
      {/* Navigation */}
      <LandingNavbar />

      {/* Hero Section */}
      <HeroSection />

      {/* Problem & Solution */}
      <ProblemSolutionSection />

      {/* 4-Element Learning-Agent Architecture */}
      <AgentArchitectureSection />

      {/* How It Works Feedback Loop */}
      <HowItWorksSection />

      {/* Features Overview */}
      <FeaturesSection />

      {/* Platform Previews */}
      <PlatformPreviewSection />

      {/* Final Call to Action & Footer */}
      <FinalCTAAndFooter />
    </div>
  );
}
