"use client";

import { useState } from "react";
import { Input, Button, message } from "antd";

const SignInPage = () => {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = () => {
    if (!email) {
      message.warning("Please enter your email address.");
      return;
    }
    setLoading(true);
    setTimeout(() => {
      message.success("Sign-in link sent! Check your email.");
      setLoading(false);
    }, 1500);
  };

  return (
    <div className="cw-signin-wrap">
      <div className="cw-signin-card">
        <div className="logo-lg">🌦</div>
        <h1>Citizen Science Weather</h1>
        <p className="lead">
          Enter the email address linked to your weather station and we&apos;ll
          send you a fresh sign-in link. <b>No password to remember.</b>
        </p>

        <div style={{ marginBottom: 6 }}>
          <label
            style={{
              display: "block",
              fontSize: 12,
              fontWeight: 600,
              color: "#4B5563",
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              marginBottom: 6,
            }}
          >
            Email address
          </label>
          <Input
            type="email"
            placeholder="sipho.dlamini@example.sz"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            size="large"
            onPressEnter={handleSubmit}
          />
        </div>

        <Button
          type="primary"
          block
          size="large"
          loading={loading}
          onClick={handleSubmit}
          style={{
            marginTop: 16,
            background: "#00B98E",
            borderColor: "#00B98E",
            fontWeight: 600,
            height: 48,
          }}
        >
          Send me a sign-in link →
        </Button>

        <div className="hint-box">
          <b>How this works</b> · Each observer looks after one weather station.
          You receive a monthly reminder email with a one-click link — no
          password. If you&apos;ve lost that email, request a new link here.
        </div>

        <div className="foot">
          If you don&apos;t have an account yet, contact UNESWA or NDRMA.
        </div>
      </div>
    </div>
  );
};

export default SignInPage;
