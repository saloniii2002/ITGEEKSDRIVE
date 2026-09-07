import React, { useState, useEffect } from "react";
import { Receipt, Check, ArrowRight, Sparkles, LayoutDashboard } from "lucide-react";
import StepUpload from "./components/StepUpload";
import StepReview from "./components/StepReview";
import StepPeople from "./components/StepPeople";
import StepAssign from "./components/StepAssign";
import StepBreakdown from "./components/StepBreakdown";
import { getShareableBreakdown } from "./api";
import MetroHero from "./components/ui/scroll-locked-video-hero";

const STEPS = [
  { id: 1, label: "Upload" },
  { id: 2, label: "Review & Correct" },
  { id: 3, label: "Add People" },
  { id: 4, label: "Assign Items" },
  { id: 5, label: "Breakdown" },
];

export default function App() {
  const [activeView, setActiveView] = useState("app"); // 'app' | 'hero'
  const [currentStep, setCurrentStep] = useState(1);
  const [billData, setBillData] = useState(null);
  const [people, setPeople] = useState([]);
  const [result, setResult] = useState(null);
  const [shareMode, setShareMode] = useState(false);
  const [loadingShare, setLoadingShare] = useState(false);
  const [shareError, setShareError] = useState(null);

  // Check if viewing a shareable link: /share/:token
  useEffect(() => {
    const path = window.location.pathname;
    if (path.startsWith("/share/")) {
      const token = path.replace("/share/", "").trim();
      if (token) {
        setShareMode(true);
        setLoadingShare(true);
        getShareableBreakdown(token)
          .then((data) => {
            setResult(data.split_result);
            setBillData({ share_token: token, bill_id: data.split_result.bill_id });
            setCurrentStep(5);
          })
          .catch((err) => {
            setShareError("Shared bill not found or expired.");
          })
          .finally(() => setLoadingShare(false));
      }
    }
  }, []);

  const handleExtractionComplete = (data) => {
    setBillData(data);
    setCurrentStep(2);
  };

  const handleConfirmComplete = (updatedBillData) => {
    setBillData(updatedBillData);
    setCurrentStep(3);
  };

  const handlePeopleComplete = (peopleList) => {
    setPeople(peopleList);
    setCurrentStep(4);
  };

  const handleCalculateComplete = (calcResult) => {
    setResult(calcResult);
    setCurrentStep(5);
  };

  const handleReset = () => {
    setBillData(null);
    setPeople([]);
    setResult(null);
    setCurrentStep(1);
    if (shareMode) {
      window.history.pushState({}, "", "/");
      setShareMode(false);
    }
  };

  if (loadingShare) {
    return (
      <div className="app-container" style={{ textAlign: "center", paddingTop: "5rem" }}>
        <h2>Loading shared bill breakdown...</h2>
      </div>
    );
  }

  if (shareError) {
    return (
      <div className="app-container" style={{ textAlign: "center", paddingTop: "5rem" }}>
        <div className="banner banner-danger" style={{ display: "inline-flex" }}>
          {shareError}
        </div>
        <div style={{ marginTop: "1rem" }}>
          <button className="btn btn-primary" onClick={handleReset}>Go to Home</button>
        </div>
      </div>
    );
  }

  if (activeView === "hero") {
    return (
      <div style={{ position: "relative", width: "100vw", height: "100vh", overflow: "hidden" }}>
        <button
          onClick={() => setActiveView("app")}
          style={{
            position: "fixed",
            top: 16,
            left: 16,
            zIndex: 99,
            display: "flex",
            alignItems: "center",
            gap: 8,
            padding: "8px 16px",
            background: "rgba(10, 15, 29, 0.75)",
            backdropFilter: "blur(12px)",
            border: "1px solid rgba(255, 255, 255, 0.15)",
            borderRadius: 999,
            color: "#f8fafc",
            fontSize: "0.85rem",
            fontWeight: 600,
            cursor: "pointer",
            boxShadow: "0 4px 20px rgba(0, 0, 0, 0.5)",
          }}
        >
          <LayoutDashboard size={16} /> Back to Bill Splitter
        </button>
        <MetroHero
          title="THE SOUNDTRACK TO EVERY STEP"
          signature={{ name: "Integrated into Bill Splitter", url: "#" }}
        />
      </div>
    );
  }

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header" style={{ position: "relative" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", width: "100%", maxWidth: 640, margin: "0 auto 0.75rem auto" }}>
          <div className="logo-badge" style={{ margin: 0 }}>
            <Receipt size={16} />
            <span>Deterministic Bill Splitter MVP</span>
          </div>
          <button
            onClick={() => setActiveView("hero")}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              background: "rgba(116, 185, 241, 0.12)",
              border: "1px solid rgba(116, 185, 241, 0.35)",
              borderRadius: 999,
              padding: "4px 12px",
              color: "#74b9f1",
              fontSize: "0.75rem",
              fontWeight: 600,
              cursor: "pointer",
              transition: "all 0.2s ease",
            }}
          >
            <Sparkles size={13} /> View Ambient Video Hero
          </button>
        </div>
        <h1 className="app-title">Split Bills Fairly & Accurately</h1>
        <p className="app-subtitle">
          Vision LLM extraction • Human review • Proportional tax & service charges • Zero rounding drift
        </p>
      </header>

      {/* Stepper Progress Bar */}
      {!shareMode && (
        <nav className="stepper" aria-label="Progress">
          {STEPS.map((step) => {
            const isActive = currentStep === step.id;
            const isCompleted = currentStep > step.id;

            return (
              <div
                key={step.id}
                className={`step-item ${isActive ? "active" : ""} ${isCompleted ? "completed" : ""}`}
              >
                <div className="step-number">
                  {isCompleted ? <Check size={14} /> : step.id}
                </div>
                <span>{step.label}</span>
              </div>
            );
          })}
        </nav>
      )}

      {/* Wizard Steps */}
      <main>
        {currentStep === 1 && (
          <StepUpload onExtractionComplete={handleExtractionComplete} />
        )}

        {currentStep === 2 && billData && (
          <StepReview
            billData={billData}
            onConfirmComplete={handleConfirmComplete}
            onBack={() => setCurrentStep(1)}
          />
        )}

        {currentStep === 3 && billData && (
          <StepPeople
            billData={billData}
            onPeopleComplete={handlePeopleComplete}
            onBack={() => setCurrentStep(2)}
          />
        )}

        {currentStep === 4 && billData && (
          <StepAssign
            billData={billData}
            people={people}
            onCalculateComplete={handleCalculateComplete}
            onBack={() => setCurrentStep(3)}
          />
        )}

        {currentStep === 5 && result && (
          <StepBreakdown
            result={result}
            billData={billData}
            onReset={handleReset}
          />
        )}
      </main>
    </div>
  );
}
