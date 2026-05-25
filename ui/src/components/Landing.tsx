import React from 'react'
import { Link } from 'react-router-dom'
import { Terminal, FileCode, Zap, Brain, Cpu, Globe, Lock, Sparkles } from 'lucide-react'

export default function Landing() {
  return (
    <div className="min-h-screen pt-24">
      {/* Hero Section */}
      <div className="max-w-7xl mx-auto px-6 py-20">
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-amber-500/20 border border-amber-500/30 mb-6">
            <Sparkles className="w-4 h-4 text-amber-400" />
            <span className="text-amber-300 text-sm font-medium">AI-Powered Development Environment</span>
          </div>
          
          <h1 className="text-6xl font-bold mb-6 bg-gradient-to-r from-amber-200 via-yellow-300 to-amber-400 bg-clip-text text-transparent">
            Devin Terminal
          </h1>
          
          <p className="text-xl text-amber-200/70 max-w-3xl mx-auto mb-8">
            Transform your development workflow with AI-powered terminal commands, intelligent file exploration, 
            and automated programming tasks. Experience the future of coding.
          </p>
          
          <div className="flex items-center justify-center gap-4">
            <Link
              to="/terminal"
              className="px-8 py-4 rounded-2xl bg-gradient-to-r from-amber-500 to-yellow-500 text-amber-950 font-bold text-lg shadow-lg shadow-amber-500/30 hover:shadow-amber-500/50 transition-all duration-300 hover:scale-105"
            >
              Launch Terminal
            </Link>
            <Link
              to="/chat"
              className="px-8 py-4 rounded-2xl bg-amber-800/30 border border-amber-600/50 text-amber-200 font-bold text-lg hover:bg-amber-800/50 transition-all duration-300"
            >
              Try AI Chat
            </Link>
          </div>
        </div>

        {/* Features Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-20">
          <FeatureCard
            icon={<Terminal className="w-8 h-8" />}
            title="AI Terminal"
            description="Execute commands with natural language. Let AI handle complex operations while you focus on logic."
            gradient="from-amber-500 to-yellow-500"
          />
          <FeatureCard
            icon={<FileCode className="w-8 h-8" />}
            title="File Explorer"
            description="Intelligent file management with hourly KPIs, automatic appraisal, and smart organization."
            gradient="from-amber-400 to-orange-500"
          />
          <FeatureCard
            icon={<Zap className="w-8 h-8" />}
            title="Task Automation"
            description="Automate repetitive programming tasks with AI-powered workflows and continuous execution."
            gradient="from-yellow-500 to-amber-600"
          />
          <FeatureCard
            icon={<Brain className="w-8 h-8" />}
            title="Code Intelligence"
            description="Understand codebases, suggest improvements, and generate documentation automatically."
            gradient="from-amber-600 to-yellow-500"
          />
          <FeatureCard
            icon={<Cpu className="w-8 h-8" />}
            title="Performance Metrics"
            description="Real-time monitoring of system resources, build times, and development velocity."
            gradient="from-orange-500 to-amber-500"
          />
          <FeatureCard
            icon={<Globe className="w-8 h-8" />}
            title="Remote Deployment"
              description="Deploy to public URLs with integrated backend services and global accessibility."
            gradient="from-yellow-400 to-amber-500"
          />
        </div>

        {/* No-Mock Functionality */}
        <div className="bg-amber-900/20 backdrop-blur-xl rounded-3xl border border-amber-700/30 p-8 mb-20">
          <div className="flex items-center gap-3 mb-6">
            <Lock className="w-6 h-6 text-amber-400" />
            <h2 className="text-2xl font-bold text-amber-200">No-Mock Functionality</h2>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <FunctionalityItem
              title="Real Terminal Execution"
              description="Actual shell command execution with full system access"
            />
            <FunctionalityItem
              title="Live File Operations"
              description="Real file system operations with instant feedback"
            />
            <FunctionalityItem
              title="True LLM Integration"
              description="Connected to actual AI models for genuine responses"
            />
            <FunctionalityItem
              title="Working Backend"
              description="Functional API endpoints with real data processing"
            />
            <FunctionalityItem
              title="Real-time Metrics"
              description="Live system monitoring and performance tracking"
            />
            <FunctionalityItem
              title="Actual Deployment"
              description="Deploy to production with public URL access"
            />
            <FunctionalityItem
              title="File Appraisal"
              description="Real file analysis with dollar value estimation"
            />
            <FunctionalityItem
              title="Task Execution"
              description="Complete programming tasks from start to finish"
            />
          </div>
        </div>

        {/* CTA Section */}
        <div className="text-center bg-gradient-to-r from-amber-500/20 via-yellow-500/20 to-amber-500/20 rounded-3xl p-12 border border-amber-600/30">
          <h2 className="text-4xl font-bold text-amber-200 mb-4">Ready to Transform Your Development?</h2>
          <p className="text-amber-300/70 mb-8 max-w-2xl mx-auto">
            Join thousands of developers using AI-powered terminals to build faster, smarter, and more efficiently.
          </p>
          <Link
            to="/terminal"
            className="inline-flex items-center gap-2 px-8 py-4 rounded-2xl bg-gradient-to-r from-amber-500 to-yellow-500 text-amber-950 font-bold text-lg shadow-lg shadow-amber-500/30 hover:shadow-amber-500/50 transition-all duration-300 hover:scale-105"
          >
            <Terminal className="w-5 h-5" />
            Get Started Now
          </Link>
        </div>
      </div>
    </div>
  )
}

function FeatureCard({ icon, title, description, gradient }: { icon: React.ReactNode, title: string, description: string, gradient: string }) {
  return (
    <div className="group bg-amber-900/20 backdrop-blur-xl rounded-2xl border border-amber-700/30 p-6 hover:border-amber-500/50 transition-all duration-300 hover:scale-105">
      <div className={`w-14 h-14 rounded-xl bg-gradient-to-br ${gradient} flex items-center justify-center mb-4 shadow-lg`}>
        <div className="text-amber-950">{icon}</div>
      </div>
      <h3 className="text-xl font-bold text-amber-200 mb-2">{title}</h3>
      <p className="text-amber-300/70 text-sm">{description}</p>
    </div>
  )
}

function FunctionalityItem({ title, description }: { title: string, description: string }) {
  return (
    <div className="flex items-start gap-3">
      <div className="w-2 h-2 rounded-full bg-amber-400 mt-2 flex-shrink-0" />
      <div>
        <h4 className="text-amber-200 font-semibold mb-1">{title}</h4>
        <p className="text-amber-400/70 text-sm">{description}</p>
      </div>
    </div>
  )
}