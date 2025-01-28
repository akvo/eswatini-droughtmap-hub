class JobTypes:
    test = 1
    verification_email = 2
    forgot_password = 3
    review_completed = 4
    review_request = 5
    initial_cdi_values = 6

    FieldStr = {
        test: "test",
        verification_email: "verification_email",
        forgot_password: "forgot_password",
        review_completed: "review_completed",
        review_request: "review_request",
        initial_cdi_values: "initial_cdi_values",
    }


class JobStatus:
    pending = 1
    on_progress = 2
    failed = 3
    done = 4

    FieldStr = {
        pending: "pending",
        on_progress: "on_progress",
        failed: "failed",
        done: "done",
    }
