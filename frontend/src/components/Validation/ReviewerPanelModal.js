"use client";

import { useCallback, useEffect, useState } from "react";
import { Alert, Button, List, Modal, Select, Tag, Tooltip } from "antd";
import { api } from "@/lib";
import { CREATE_PUBLICATION_MAIL } from "@/static/config";

/**
 * Add or remove reviewers on an existing publication.
 *
 * Reviewers used to be settable only at creation, so a publication assigned a
 * single Technical Working Group was stuck that way for life — every Inkhundla
 * trivially "ready" off one institution's response. This is the repair path
 * (design D-11).
 *
 * The rules are asymmetric and enforced server-side; the disabled states here
 * are a courtesy, not the control:
 *   - adding is allowed while in review or in validation
 *   - removing is allowed only in review, and only before they have submitted
 *
 * Adding is **staged**. "Add" only queues someone locally; nothing is written
 * and no email leaves until "Send invitations" is pressed. Writing on each Add
 * meant a mis-clicked reviewer was already invited by the time the admin
 * removed them — an email cannot be recalled, so the undo has to exist before
 * the send, not after it.
 */
const ReviewerPanelModal = ({ open, publicationId, onClose, onChanged }) => {
  const [panel, setPanel] = useState([]);
  const [pending, setPending] = useState([]);
  const [yearMonth, setYearMonth] = useState(null);
  const [candidates, setCandidates] = useState([]);
  const [selected, setSelected] = useState([]);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [publication, reviewers] = await Promise.all([
        api("GET", `/admin/publication/${publicationId}`),
        api("GET", "/admin/reviewers?page=1"),
      ]);
      setPanel(publication?.reviewers || []);
      setYearMonth(publication?.year_month || null);
      setCandidates(reviewers?.data || []);
    } catch (err) {
      console.error(err);
      setError("Could not load the reviewer panel.");
    } finally {
      setLoading(false);
    }
  }, [publicationId]);

  useEffect(() => {
    if (open) {
      load();
    }
  }, [load, open]);

  const assignedIds = new Set([
    ...panel.map((r) => r.id),
    ...pending.map((r) => r.id),
  ]);

  /** Queue locally. No request, so this is freely undoable. */
  const stage = () => {
    setError(null);
    setPending((current) => [
      ...current,
      ...candidates.filter((c) => selected.includes(c.id)),
    ]);
    setSelected([]);
  };

  const unstage = (reviewer) =>
    setPending((current) => current.filter((r) => r.id !== reviewer.id));

  /** The only place a Review row is created and an invitation goes out. */
  const sendInvitations = async () => {
    setBusy(true);
    setError(null);
    try {
      // api() resolves on 4xx, so a refusal is a body — never a throw.
      const res = await api(
        "POST",
        `/admin/publication-reviewers/${publicationId}`,
        {
          reviewers: pending.map((r) => r.id),
          // Without these the server has nothing to send and silently skips
          // the invitation, so the reviewer is assigned work they are never
          // told about. Same template the create form uses; the {{...}}
          // placeholders are substituted server-side by the same function
          // that mails the original panel.
          subject:
            `${CREATE_PUBLICATION_MAIL.subject} ${yearMonth || ""}`.trim(),
          message: CREATE_PUBLICATION_MAIL.message,
        },
      );
      if (typeof res?.added !== "number") {
        setError(res?.reviewers?.[0] || "Could not add those reviewers.");
        return;
      }
      setPending([]);
      await load();
      onChanged?.();
      onClose?.();
    } finally {
      setBusy(false);
    }
  };

  const close = () => {
    if (pending.length) {
      Modal.confirm({
        title: "Discard the reviewers you have not invited?",
        content: `${pending.length} reviewer${
          pending.length > 1 ? "s have" : " has"
        } been queued but not invited. Closing now discards them.`,
        okText: "Discard",
        onOk: () => {
          setPending([]);
          onClose?.();
        },
      });
      return;
    }
    onClose?.();
  };

  const remove = async (reviewer) => {
    setBusy(true);
    setError(null);
    try {
      const res = await api(
        "DELETE",
        `/admin/publication-reviewers/${publicationId}/${reviewer.id}`,
      );
      // 204 gives an empty body; anything with `reviewers` is a refusal.
      if (res?.reviewers) {
        setError(res.reviewers[0]);
        return;
      }
      await load();
      onChanged?.();
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal
      open={open}
      onCancel={close}
      title="Reviewer panel"
      footer={[
        <Button key="close" onClick={close}>
          Close
        </Button>,
        <Button
          key="send"
          type="primary"
          disabled={!pending.length || busy}
          loading={busy}
          onClick={sendInvitations}
        >
          {pending.length
            ? `Send ${pending.length} invitation${
                pending.length > 1 ? "s" : ""
              }`
            : "Send invitations"}
        </Button>,
      ]}
      width={560}
    >
      <div className="flex flex-col gap-4 py-2">
        {error && <Alert type="error" message={error} showIcon />}

        <List
          size="small"
          loading={loading}
          dataSource={[
            ...panel,
            ...pending.map((r) => ({ ...r, staged: true })),
          ]}
          locale={{ emptyText: "No reviewers assigned." }}
          renderItem={(reviewer) => (
            <List.Item
              actions={[
                reviewer.staged ? (
                  // Nothing has been written or sent yet, so this is a plain
                  // undo — no request, no refusal, no email already gone.
                  <Button
                    key="unstage"
                    type="link"
                    onClick={() => unstage(reviewer)}
                  >
                    Undo
                  </Button>
                ) : reviewer.is_completed ? (
                  <Tooltip
                    key="locked"
                    title="They have already submitted a review, which other
                      decisions were made against. Removing it would change
                      numbers the validator has already acted on."
                  >
                    <span className="text-xs text-[#a4a4a4]">Locked</span>
                  </Tooltip>
                ) : (
                  <Button
                    key="remove"
                    type="link"
                    danger
                    disabled={busy}
                    onClick={() => remove(reviewer)}
                  >
                    Remove
                  </Button>
                ),
              ]}
            >
              <List.Item.Meta
                title={reviewer.name}
                description={
                  <span className="flex flex-wrap items-center gap-2">
                    <span className="text-xs">
                      {reviewer.technical_working_group || "No working group"}
                    </span>
                    {reviewer.staged && <Tag color="#f39c12">Not invited</Tag>}
                    {reviewer.is_completed && (
                      <Tag color="#12b76a">Submitted</Tag>
                    )}
                  </span>
                }
              />
            </List.Item>
          )}
        />

        <div className="flex items-center gap-2">
          <Select
            mode="multiple"
            className="flex-1"
            placeholder="Add reviewers"
            value={selected}
            onChange={setSelected}
            optionFilterProp="label"
            options={candidates
              .filter((c) => !assignedIds.has(c.id))
              .map((c) => ({
                value: c.id,
                label: `${c.name} — ${
                  c.technical_working_group || "No working group"
                }`,
              }))}
          />
          <Button disabled={!selected.length || busy} onClick={stage}>
            Add
          </Button>
        </div>
        <span className="text-xs text-[#606060]">
          {pending.length
            ? "No one has been invited yet. Review the list, then send the invitations."
            : "Add queues a reviewer. Nothing is saved and no email is sent until you send the invitations."}
        </span>
      </div>
    </Modal>
  );
};

export default ReviewerPanelModal;
