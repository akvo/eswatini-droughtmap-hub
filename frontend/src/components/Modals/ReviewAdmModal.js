"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Button,
  Flex,
  Form,
  Input,
  Modal,
  Select,
  Spin,
  Tag,
  message,
} from "antd";
import { useAppContext, useAppDispatch } from "@/context/AppContextProvider";
import { ConfidenceBadge, DroughtScore } from "@/components/DS";
import {
  DROUGHT_CATEGORY,
  DROUGHT_CATEGORY_LABEL,
  DROUGHT_CATEGORY_VALUE,
} from "@/static/config";
import { api } from "@/lib";

const { TextArea } = Input;
const { useForm } = Form;

/** A computed class exists. Note category 0 (normal) is a value, not "missing". */
const isComputed = (category) =>
  category !== undefined &&
  category !== null &&
  category !== DROUGHT_CATEGORY_VALUE.none;

/**
 * Individual Inkhundla review (design D-7 — a modal for this iteration).
 *
 * Context comes from GET /reviewer/{publication_id}/administrations/{id}; the
 * write path stays the review PUT, which replaces the whole suggestion_values
 * array.
 */
const ReviewAdmModal = ({ review, publicationId, onSubmitted }) => {
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [showSuggestion, setShowSuggestion] = useState(false);
  const { activeAdm } = useAppContext();
  const appDispatch = useAppDispatch();
  const [form] = useForm();

  const administrationId = activeAdm?.administration_id;
  const isOpen = useMemo(() => Boolean(administrationId), [administrationId]);

  const row = detail?.administration;
  const suggestion = detail?.my_review?.suggestion;
  const isReviewed = Boolean(suggestion?.reviewed);
  const isCompleted = Boolean(review?.is_completed);
  const computed = row?.cdi_class;
  const hasComputed = isComputed(computed);

  const loadDetail = useCallback(async () => {
    if (!administrationId || !publicationId) {
      return;
    }
    try {
      setLoading(true);
      const data = await api(
        "GET",
        `/reviewer/${publicationId}/administrations/${administrationId}`,
      );
      setDetail(data);
      const own = data?.my_review?.suggestion;
      // Nothing to approve when there is no computed class -> open in suggest mode.
      setShowSuggestion(
        !own?.reviewed && !isComputed(data?.administration?.cdi_class),
      );
      form.setFieldsValue({
        suggestedCategory: own?.category,
        comment: own?.comment || "",
      });
    } catch (err) {
      console.error(err);
      message.error("Could not load this Inkhundla.");
    } finally {
      setLoading(false);
    }
  }, [administrationId, publicationId, form]);

  useEffect(() => {
    if (isOpen) {
      loadDetail();
    }
  }, [isOpen, loadDetail]);

  const onClose = () => {
    setDetail(null);
    setShowSuggestion(false);
    form.resetFields();
    appDispatch({ type: "REMOVE_ACTIVE_ADM" });
  };

  const onFinish = async (values) => {
    try {
      setSaving(true);
      const base = review?.suggestion_values?.length
        ? review.suggestion_values
        : review?.publication?.initial_values || [];
      const suggestion_values = base.map((value) => {
        if (value?.administration_id !== administrationId) {
          return value;
        }
        return {
          ...value,
          category: showSuggestion ? values.suggestedCategory : computed,
          comment: values.comment || "",
          reviewed: true,
        };
      });
      await api("PUT", `/reviewer/review/${review?.id}`, { suggestion_values });
      onClose();
      await onSubmitted?.();
    } catch (err) {
      console.error(err);
      message.error("An error occurred, please report this issue!");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      title="Inkhundla status"
      open={isOpen}
      onCancel={onClose}
      maskClosable={false}
      width={768}
      destroyOnClose
      transitionName=""
      maskTransitionName=""
      footer={
        <Flex align="center" justify="space-between">
          {!isCompleted && (
            <Button
              type="primary"
              ghost
              disabled={loading}
              onClick={() => setShowSuggestion(!showSuggestion)}
            >
              {showSuggestion ? "Cancel" : "Suggest new value"}
            </Button>
          )}
          <Button
            type="primary"
            loading={saving}
            disabled={
              loading || isCompleted || (!showSuggestion && !hasComputed) // nothing to approve
            }
            onClick={() => form.submit()}
          >
            {showSuggestion ? "Suggest new value" : "Approve computed value"}
          </Button>
        </Flex>
      }
    >
      {/* The Form must live INSIDE the Modal: the Modal renders through a
          portal, so a Form wrapped around it leaves the fields in a different
          tree from the <form> element and form.submit() silently does nothing. */}
      <Form form={form} onFinish={onFinish} layout="vertical">
        {loading || !row ? (
          <Flex align="center" justify="center" className="py-12">
            <Spin />
          </Flex>
        ) : (
          <div className="w-full space-y-4">
            <Flex align="center" justify="space-between">
              <div className="flex flex-col">
                <h3 className="text-xl font-semibold text-[#333333]">
                  {row?.name || activeAdm?.name}
                </h3>
                <span className="text-sm text-[#a4a4a4]">{row?.region}</span>
              </div>
              <Tag color={isReviewed ? "green" : "default"}>
                {isReviewed ? "Reviewed" : "Not reviewed"}
              </Tag>
            </Flex>

            <div className="flex flex-wrap items-center gap-6 border-y border-[#eaecf0] py-3">
              <div className="flex flex-col gap-1">
                <span className="text-sm text-[#606060]">Computed value</span>
                <span className="flex items-center gap-2">
                  <DroughtScore level={computed} />
                  <span className="text-sm text-[#333333]">
                    {DROUGHT_CATEGORY_LABEL?.[computed]}
                  </span>
                </span>
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-sm text-[#606060]">Confidence</span>
                <ConfidenceBadge
                  band={row?.confidence?.band}
                  isMock={row?.confidence?.is_mock}
                />
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-sm text-[#606060]">Reviews</span>
                <span className="text-sm text-[#333333]">
                  {row?.reviews?.completed}/{row?.reviews?.total}
                  {row?.disputed && (
                    <span className="ml-2 text-[#B10D0B]">
                      disagreement detected
                    </span>
                  )}
                </span>
              </div>
            </div>

            {showSuggestion && (
              <Form.Item
                label="Suggested value"
                name="suggestedCategory"
                rules={[
                  {
                    required: true,
                    message: "Please select a drought category",
                  },
                ]}
              >
                <Select
                  options={DROUGHT_CATEGORY.filter(
                    (c) => c.value !== DROUGHT_CATEGORY_VALUE.none,
                  )}
                  placeholder="Select drought category"
                  allowClear={false}
                />
              </Form.Item>
            )}

            <Form.Item
              name="comment"
              label="Comment"
              rules={[
                {
                  required: showSuggestion,
                  message: "Please provide a comment",
                },
              ]}
            >
              <TextArea
                rows={3}
                placeholder="Add a comment"
                disabled={isCompleted}
              />
            </Form.Item>
          </div>
        )}
      </Form>
    </Modal>
  );
};

export default ReviewAdmModal;
