"use client";

import { useEffect, useState, useMemo } from "react";
import {
  Button,
  DatePicker,
  Form,
  Input,
  TreeSelect,
  message,
  Col,
  Row,
  Spin,
} from "antd";
import { CalendarOutlined } from "@ant-design/icons";
import { SubmitButton } from "../Buttons";
import TinyEditor from "../TinyEditor";
import ComponentRasterPreview from "../ComponentRasterPreview";
import dayjs from "dayjs";
import { api } from "@/lib";
import {
  CREATE_PUBLICATION_MAIL,
  MIN_TWGS_PER_PUBLICATION,
} from "@/static/config";

const { useForm } = Form;

const StartPublicationSlideIn = ({ geonode, visible, onClose, onSuccess }) => {
  const [reviewerTree, setReviewerTree] = useState([]);
  const [loading, setLoading] = useState(false);
  const [fetchingReviewers, setFetchingReviewers] = useState(false);
  const [errors, setErrors] = useState(null);
  const [form] = useForm();

  const yearMonth = Form.useWatch("year_month", form);

  // Fetch reviewer tree data on mount or when slide-in opens
  useEffect(() => {
    if (visible) {
      const fetchReviewerTree = async () => {
        setFetchingReviewers(true);
        try {
          const res = await api("GET", "/admin/reviewers-tree");
          setReviewerTree(res || []);
        } catch (err) {
          console.error(err);
          message.error("Failed to load reviewer list.");
        } finally {
          setFetchingReviewers(false);
        }
      };
      fetchReviewerTree();
    }
  }, [visible]);

  // Reset form when geonode changes or slide-in opens/closes
  useEffect(() => {
    if (visible && geonode) {
      form.setFieldsValue({
        year_month: geonode?.year_month ? dayjs(geonode.year_month) : null,
        due_date: null,
        subject: geonode?.year_month
          ? `${CREATE_PUBLICATION_MAIL?.subject} ${dayjs(geonode.year_month).format("YYYY-MM")}`
          : CREATE_PUBLICATION_MAIL?.subject || "",
        message: CREATE_PUBLICATION_MAIL?.message || "",
        reviewers: [],
      });
      setErrors(null);
    } else {
      form.resetFields();
    }
  }, [visible, geonode, form]);

  // Build userId -> group node lookup
  const userGroupMap = useMemo(() => {
    const map = {};
    reviewerTree.forEach((group) => {
      group.children?.forEach((leaf) => {
        map[leaf.value] = group;
      });
    });
    return map;
  }, [reviewerTree]);

  const onFinish = async (values) => {
    setLoading(true);
    setErrors(null);
    try {
      const payload = {
        cdi_geonode_id: geonode?.pk,
        due_date: values.due_date
          ? dayjs(values.due_date).format("YYYY-MM-DD")
          : null,
        year_month: values.year_month
          ? dayjs(values.year_month).format("YYYY-MM-DD")
          : null,
        subject: values.subject,
        message: values.message,
        reviewers: values.reviewers || [],
        initial_values: [],
        download_url: geonode?.download_url,
      };

      const res = await api("POST", "/admin/publications", payload);
      if (res?.id) {
        message.success("New publication successfully created");
        onSuccess();
      } else {
        setErrors(res);
      }
    } catch (err) {
      console.error(err);
      message.error("[ADM-P-1] Please report this issue along with the code.");
    } finally {
      setLoading(false);
    }
  };

  if (!visible) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Slide-in Container */}
      <div className="relative w-[604px] h-screen bg-white flex flex-col shadow-2xl z-10 border-l border-[#D2D2D2]">
        {/* Sticky Header */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-[#D2D2D2] sticky top-0 bg-white z-10">
          <span className="text-base font-semibold text-neutral-800">
            Start new publication
          </span>
          <button
            onClick={onClose}
            className="text-neutral-500 hover:text-neutral-700 text-lg font-semibold"
          >
            &times;
          </button>
        </div>

        {/* Form Body Area */}
        <div className="flex-1 overflow-y-auto px-6 py-6 flex flex-col gap-6">
          <p className="text-[#606060] text-sm border-b border-[#D2D2D2] pb-4">
            Pick the sector and write a clear title + description. The Protocol
            ID is auto-generated from the sector on save.
          </p>

          <Form form={form} onFinish={onFinish} layout="vertical">
            {fetchingReviewers ? (
              <div className="flex flex-col items-center justify-center py-8 gap-2">
                <Spin />
                <span className="text-neutral-500 text-sm">
                  Loading reviewers...
                </span>
              </div>
            ) : (
              <>
                <Form.Item
                  label="Select the reviewer"
                  name="reviewers"
                  rules={[
                    {
                      validator: async (_, values) => {
                        if (!values || !values.length) {
                          return Promise.reject(
                            new Error("Please select at least one reviewer."),
                          );
                        }
                        const selectedGroups = new Set(
                          values
                            .map((id) => userGroupMap[id])
                            .filter((g) => g && g.value !== "twg-unassigned")
                            .map((g) => g.value),
                        );
                        if (selectedGroups.size < MIN_TWGS_PER_PUBLICATION) {
                          return Promise.reject(
                            new Error(
                              `Please select reviewers from at least ${MIN_TWGS_PER_PUBLICATION} different Technical Working Groups.`,
                            ),
                          );
                        }
                      },
                    },
                  ]}
                >
                  <TreeSelect
                    treeData={reviewerTree}
                    multiple
                    treeCheckable
                    showCheckedStrategy={TreeSelect.SHOW_CHILD}
                    placeholder="Select team member"
                    treeNodeLabelProp="title"
                    treeNodeFilterProp="title"
                    showSearch
                    style={{ width: "100%" }}
                    labelRender={({ value, label }) => {
                      const group = userGroupMap[value];
                      const abbrev = (group?.title || "").split(" (")[0];
                      return abbrev ? `${label} (${abbrev})` : label;
                    }}
                  />
                </Form.Item>

                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item
                      label="Publication Date"
                      name="year_month"
                      rules={[
                        {
                          required: true,
                          message: "Publication date is required.",
                        },
                      ]}
                    >
                      <DatePicker
                        picker="month"
                        style={{ width: "100%" }}
                        prefix={
                          <CalendarOutlined className="text-neutral-300" />
                        }
                        suffixIcon={null}
                        onChange={(date) => {
                          if (date) {
                            form.setFieldValue(
                              "subject",
                              `${CREATE_PUBLICATION_MAIL?.subject} ${dayjs(date).format("YYYY-MM")}`,
                            );
                          }
                        }}
                      />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item
                      label="Review Deadline"
                      name="due_date"
                      rules={[
                        {
                          validator: (_, value) => {
                            if (!value) {
                              return Promise.reject(
                                "Review deadline is required.",
                              );
                            }
                            return Promise.resolve();
                          },
                        },
                      ]}
                      help={errors?.due_date?.join(", ")}
                      validateStatus={errors?.due_date ? "error" : null}
                    >
                      <DatePicker
                        style={{ width: "100%" }}
                        prefix={
                          <CalendarOutlined className="text-neutral-300" />
                        }
                        suffixIcon={null}
                      />
                    </Form.Item>
                  </Col>
                </Row>

                <Form.Item
                  label="Subject"
                  name="subject"
                  rules={[{ required: true, message: "Subject is required." }]}
                >
                  <Input />
                </Form.Item>

                <Form.Item
                  label="Message"
                  name="message"
                  rules={[{ required: true, message: "Message is required." }]}
                >
                  {/* TinyEditor component needs the value/setValue context to function */}
                  {visible && (
                    <Form.Item noStyle shouldUpdate>
                      {({ getFieldValue, setFieldValue }) => (
                        <TinyEditor
                          value={getFieldValue("message")}
                          setValue={(v) => setFieldValue("message", v)}
                          height={325}
                        />
                      )}
                    </Form.Item>
                  )}
                </Form.Item>

                <div className="mt-4 border-t border-[#D2D2D2] pt-4">
                  <ComponentRasterPreview yearMonth={yearMonth} />
                </div>
              </>
            )}
          </Form>
        </div>

        {/* Sticky Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-[#D2D2D2] sticky bottom-0 bg-white z-10">
          <Button onClick={onClose} disabled={loading}>
            Cancel
          </Button>
          <SubmitButton
            form={form}
            loading={loading}
            disabled={fetchingReviewers}
            onClick={() => form.submit()}
          >
            Create
          </SubmitButton>
        </div>
      </div>
    </div>
  );
};

export default StartPublicationSlideIn;
