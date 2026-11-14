import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, postChat } from "../../shared/api/client";
import { MatchChat } from "./match-chat";
import type * as ChatClient from "../../shared/api/client";

vi.mock("../../shared/api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof ChatClient>()),
  postChat: vi.fn(),
}));

const postChatMock = vi.mocked(postChat);

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

beforeEach(() => postChatMock.mockReset());

describe("MatchChat", () => {
  it("sends a question and shows the answer in the conversation", async () => {
    postChatMock.mockResolvedValue({
      answer: "Barcelona plays on Tuesday.",
      outcome: "answered",
    });
    const user = userEvent.setup();
    render(<MatchChat />);

    await user.type(screen.getByLabelText("Your question"), "Next match?");
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(
      await screen.findByText("Barcelona plays on Tuesday."),
    ).toBeInTheDocument();
    expect(screen.getByText("Next match?")).toBeInTheDocument();
    expect(postChatMock).toHaveBeenCalledWith(
      [{ role: "user", content: "Next match?" }],
      expect.any(AbortSignal),
    );
    expect(screen.getByLabelText("Your question")).toHaveValue("");
  });

  it("sends the earlier turns with a follow-up question", async () => {
    postChatMock
      .mockResolvedValueOnce({ answer: "Hello!", outcome: "answered" })
      .mockResolvedValueOnce({ answer: "Done.", outcome: "answered" });
    const user = userEvent.setup();
    render(<MatchChat />);
    const input = screen.getByLabelText("Your question");

    await user.type(input, "Hi{Enter}");
    await screen.findByText("Hello!");
    await user.type(input, "And then?{Enter}");
    await screen.findByText("Done.");

    expect(postChatMock).toHaveBeenLastCalledWith(
      [
        { role: "user", content: "Hi" },
        { role: "assistant", content: "Hello!" },
        { role: "user", content: "And then?" },
      ],
      expect.any(AbortSignal),
    );
  });

  it("keeps Send disabled for blank input and inserts a newline on Shift+Enter", async () => {
    const user = userEvent.setup();
    render(<MatchChat />);
    const input = screen.getByLabelText("Your question");
    const send = screen.getByRole("button", { name: "Send" });

    expect(send).toBeDisabled();
    await user.type(input, "   ");
    expect(send).toBeDisabled();
    await user.clear(input);
    await user.type(input, "a{Shift>}{Enter}{/Shift}b");

    expect(input).toHaveValue("a\nb");
    expect(postChatMock).not.toHaveBeenCalled();
  });

  it("disables sending while a request is pending and ignores a second submit", async () => {
    const pending = deferred<{ answer: string; outcome: "answered" }>();
    postChatMock.mockReturnValue(pending.promise);
    const user = userEvent.setup();
    render(<MatchChat />);
    const input = screen.getByLabelText("Your question");

    await user.type(input, "First{Enter}");
    expect(await screen.findByRole("status")).toHaveTextContent(
      "Looking through the match data",
    );
    await user.type(input, "Second{Enter}");
    expect(screen.getByRole("button", { name: "Sending…" })).toBeDisabled();
    expect(postChatMock).toHaveBeenCalledOnce();

    pending.resolve({ answer: "Answer.", outcome: "answered" });
    expect(await screen.findByText("Answer.")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("status")).toBeNull());
  });

  it("restores the question and shows an alert when the request fails", async () => {
    postChatMock.mockRejectedValue(
      new ApiError("Too many questions. Try again in 5 seconds.", 429),
    );
    const user = userEvent.setup();
    render(<MatchChat />);

    await user.type(screen.getByLabelText("Your question"), "Next match?");
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Too many questions. Try again in 5 seconds.",
    );
    expect(screen.getByLabelText("Your question")).toHaveValue("Next match?");
    expect(screen.queryByText("You")).toBeNull();
  });

  it("shows a generic message for an unexpected failure and clears it on the next send", async () => {
    postChatMock
      .mockRejectedValueOnce(new Error("boom"))
      .mockResolvedValueOnce({ answer: "Fine now.", outcome: "answered" });
    const user = userEvent.setup();
    render(<MatchChat />);

    await user.type(screen.getByLabelText("Your question"), "Hi{Enter}");
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Something went wrong. Try again in a moment.",
    );
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByText("Fine now.")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("asks an example question when it is clicked", async () => {
    postChatMock.mockResolvedValue({ answer: "Here.", outcome: "answered" });
    const user = userEvent.setup();
    render(<MatchChat />);

    await user.click(
      screen.getByRole("button", { name: "Show the latest finished matches." }),
    );

    expect(await screen.findByText("Here.")).toBeInTheDocument();
    expect(postChatMock).toHaveBeenCalledWith(
      [{ role: "user", content: "Show the latest finished matches." }],
      expect.any(AbortSignal),
    );
  });

  it("limits the question length", () => {
    render(<MatchChat />);
    expect(screen.getByLabelText("Your question")).toHaveAttribute(
      "maxlength",
      "1000",
    );
  });
});
