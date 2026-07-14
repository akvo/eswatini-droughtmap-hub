"use client";

import { useCallback, useEffect, useState } from "react";
import { Button, Flex, Modal, Spin, message } from "antd";
import { DroughtScore } from "@/components/DS";
import { DROUGHT_CATEGORY_LABEL } from "@/static/config";
import { api } from "@/lib";

/** Rows shown before "Show all" expands the list (Figma 3387:40536). */
const PREVIEW_SIZE = 7;

const AlertIcon = () => (
  <span className="flex h-12 w-12 items-center justify-center rounded-[28px] bg-brandTint text-[#3E5EB9]">
    <svg
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z" />
      <path d="M12 9v4M12 17h.01" />
    </svg>
  </span>
);

const PlusIcon = () => (
  <svg
    width="16"
    height="16"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    aria-hidden
  >
    <path d="M12 5v14M5 12h14" />
  </svg>
);

/**
 * Bulk-accept confirmation (Figma 3387:40536).
 *
 * Owns the fetch of the high-confidence rows so the dialog shows exactly what
 * will be written; the parent performs the single review PUT (design D-5).
 */
const BulkAcceptModal = ({
  open,
  publicationId,
  saving = false,
  onAccept,
  onClose,
}) => {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showAll, setShowAll] = useState(false);

  const loadRows = useCallback(async () => {
    try {
      setLoading(true);
      const { data = [] } = await api(
        "GET",
        `/reviewer/${publicationId}/administrations?confidence=high&page_size=100`,
      );
      // Only what is still pending: bulk accept must never overwrite a class
      // this reviewer already approved or suggested by hand.
      setRows(data.filter((row) => !row?.my_suggestion?.reviewed));
    } catch (err) {
      console.error(err);
      message.error("Could not load the high-confidence Tinkhundla.");
    } finally {
      setLoading(false);
    }
  }, [publicationId]);

  useEffect(() => {
    if (open) {
      setShowAll(false);
      loadRows();
    }
  }, [open, loadRows]);

  const visible = showAll ? rows : rows.slice(0, PREVIEW_SIZE);
  const hidden = rows.length - visible.length;

  return (
    <Modal
      open={open}
      onCancel={onClose}
      width={400}
      centered
      closable={false}
      footer={null}
      destroyOnClose
    >
      <div className="flex flex-col gap-8">
        <div className="flex flex-col gap-5">
          <AlertIcon />
          <div className="flex flex-col gap-2">
            <h2 className="text-xl font-medium leading-[30px] text-[#333333]">
              Bulk accept high confidence
            </h2>
            <p className="text-base leading-6 text-[#606060]">
              Mark all selected as reviewed?
            </p>
          </div>
        </div>

        {loading ? (
          <Flex align="center" justify="center" className="py-10">
            <Spin />
          </Flex>
        ) : (
          <div className="flex flex-col border border-[#d2d2d2]">
            <div className="flex items-center border-b border-[#d2d2d2] bg-[#e8e8e8] text-xs leading-[18px] text-[#606060]">
              <span className="flex-1 px-2 py-3">Inkhundla</span>
              <span className="flex-1 px-2 py-3">Condition</span>
              <span className="w-[86px] px-2 py-3">Score</span>
            </div>
            <div
              className={showAll ? "max-h-[320px] overflow-y-auto" : undefined}
            >
              {visible.map((row) => (
                <div
                  key={row.administration_id}
                  className="flex items-center border-b border-[#d2d2d2]"
                >
                  <span className="flex-1 px-4 py-3 text-sm font-medium leading-5 text-[#333333]">
                    {row.name}
                  </span>
                  <span className="flex-1 px-2 py-3 text-sm leading-5 text-[#606060] opacity-25">
                    {DROUGHT_CATEGORY_LABEL?.[row.cdi_class]}
                  </span>
                  <span className="w-[86px] px-2 py-3">
                    <DroughtScore level={row.cdi_class} />
                  </span>
                </div>
              ))}
            </div>
            {hidden > 0 && (
              <Button
                className="w-full border-0"
                icon={<PlusIcon />}
                onClick={() => setShowAll(true)}
              >
                Show all
              </Button>
            )}
          </div>
        )}

        <div className="flex items-center gap-3">
          <Button className="flex-1" onClick={onClose} disabled={saving}>
            Discard
          </Button>
          <Button
            type="primary"
            className="flex-1"
            loading={saving}
            disabled={loading || !rows.length}
            onClick={() => onAccept(rows)}
          >
            Accept all
          </Button>
        </div>
      </div>
    </Modal>
  );
};

export default BulkAcceptModal;
