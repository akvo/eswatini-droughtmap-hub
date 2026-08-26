"use client";

import { useState, useEffect } from "react";
import { Button, Form } from "antd";

const SubmitButton = ({
  form,
  children,
  type = "primary",
  size = "large",
  ...props
}) => {
  const [submittable, setSubmittable] = useState(false);
  // Watch all values
  const values = Form.useWatch([], form);
  useEffect(() => {
    form
      .validateFields({
        validateOnly: true,
      })
      .then(() => setSubmittable(true))
      .catch((err) => {
        if (err && err.outOfDate) {
          return;
        }
        setSubmittable(false);
      });
  }, [form, values]);
  return (
    <Button
      type={type}
      size={size}
      htmlType="submit"
      {...props}
      disabled={!submittable || props.disabled}
    >
      {children}
    </Button>
  );
};

export default SubmitButton;
