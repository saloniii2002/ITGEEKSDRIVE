import React, { useState, useEffect } from "react";
import { Receipt, Check, ArrowRight } from "lucide-react";
import StepUpload from "./components/StepUpload";
import StepReview from "./components/StepReview";
import StepPeople from "./components/StepPeople";
import StepAssign from "./components/StepAssign";
import StepBreakdown from "./components/StepBreakdown";
import { getShareableBreakdown } from "./api";

const STEPS = [
  { id: 1, label: "Upload" },
  { id: 2, label: "Review & Correct" },
  { id: 3, label: "Add People" },
  { id: 4, label: "Assign Items" },
  { id: 5, label: "Breakdown" },
];

export default function App() {
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

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="logo-badge">
          <Receipt size={16} />
          <span>Deterministic Bill Splitter MVP</span>
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
