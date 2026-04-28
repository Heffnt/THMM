# Project, like a Pro

## Contents

- [1. General Information](#1-general-information)
- [2. Proposal Guide](#2-proposal-guide)
  - [2.1. Grading Criteria for Proposals](#21-grading-criteria-for-proposals)
  - [2.2. Recommended Structure for Proposals](#22-recommended-structure-for-proposals)
- [3. Proposal Peer Review Guide](#3-proposal-peer-review-guide)
- [4. Final Report and Artifact Guide](#4-final-report-and-artifact-guide)
  - [4.1. Project Report](#41-project-report)
  - [4.2. Team Report](#42-team-report)
  - [4.3. Artifact](#43-artifact)
  - [4.4. Grading Criteria for Artifacts](#44-grading-criteria-for-artifacts)
- [5. Additional Resources](#5-additional-resources)
  - [5.1. LLM Policy](#51-llm-policy)
  - [5.2. SWEET Center For Team Work](#52-sweet-center-for-team-work)

## 1. General Information

Students form teams to produce a project in the second half of the semester. The project should be programming-language adjacent. Below are examples of types of projects students can take:

- Implement a toy language that focuses on showcasing a neat feature which can aid implementation and/or verification in a domain that the student is familiar with.
- Make innovative use of an advanced programming language feature (like affine types in rust, type classes in Haskell, etc.) to implement a library for a domain that the student is familiar with.
- Produce a written paper that specifies a language which can aid implementation and verification in a specific domain. The written paper needs to describe the syntax of the language, and the algorithms / data structures used in detail.

All the submissions and activities are listed below, with:

1. Whether there is a required gradescope submission.
2. Percentage of the final grade.
3. The section to find more details on the subject.

In particular, the preliminary proposal is required to be submitted on gradescope, but it is for feedback only, thus does not count towards the final grade. The final presentation does not require a gradescope submission, but it counts towards 6% of the final grade.

| Activity | Submission | Grade Weight | Details |
| --- | --- | --- | --- |
| Finding a Team | No submission | N/A | N/A |
| Preliminary Proposal | Submission | 0% | See Section 2 |
| Peer Review | Submission | 6% | See Section 3 |
| Final Proposal | Submission | 6% | See Section 2 |
| Final Reports & Artifact | Submission | 6% | See Section 4 |
| Final Presentation | No submission | 6% | N/A |

Note: All of these submissions need to be in readable and standard formats like pdf, odf, and/or markdown; OOXML (or docx) produced by MS Word is not a standard format.

Finally, here are some additional details and recommendation for the project:

- Finding a Team: It is recommended to find your group as soon as possible around midterm. You need to find a team before the final proposal is due. Otherwise, it may be difficult to contribute meaningful work to project, which could lead to a lower score.
- Team Composition: Your team need to consist of 1-5 students. However, having more than 3 students in your team is recommended for the following reasons:
  - It would be easier to settle dispute regarding unfair work division: see Section 4.2 and Section 4.4 for more details on reporting unfair work divisions.
  - In general, with more students, it is more likely to produce a better project, scoring higher points.
  - More practically, with more teams, each team will get less time to present their results, if there are too many teams, I might dedicate two classes to presentations.

## 2. Proposal Guide

The proposal serves as a written document to your envisioned specification for the project and how you aim to achieve this vision with your teammates. Common misconceptions surrounding the proposal includes the following:

- "The code is the specification": if the code is the specification, then all software always satisfy their specifications, making all the software bug-free. However, almost all software in existence has bugs. To determine whether a behavior is a bug or a feature, it is helpful to have a formal or informal specification written down as reference. This approach is similar to stating your hypothesis before running the experiment in science, where the hypothesis is part of the specification for the designed experiment.
- "Proposal happens strictly before the implementation": initial prototyping can provide clarity in the approach to implement the specification, which serves as the action plan in your proposal. Action plans are often developed with the guidance of prototyping, and thus don't wait until the proposal is due to start your implementation.

### 2.1. Grading Criteria for Proposals

Grading of proposal is out of 60 points with 10 points extra credit, taking up 6% of the final grade:

- [20 points] Comprehensive Background: whether the background survey provides a good summary of the current approaches, and whether the comparison between them is fair and understandable for people with undergraduate education in computer science.
- [20 points] Clarity in the Action Plan: whether the action plan is reasonable to accomplish the desired goal, whether the action plan is concrete enough to follow, and whether the limitation of the action plan is fairly presented.
- [10 points] Merit and Innovation: compare to existing work in the domain, whether the proposed work brings benefit to the domain expert and/or designers targeting this domain.
- [10 points] Clarity in Presentation: whether the structure of the proposal is clear and easy to read, and whether the problems and solutions are sufficiently motivated and cleanly presented.
- [10 points] Extra Credit: clearly presented examples, neat typesetting, clear and illustrative graphs, and significant innovation in the domain will be awarded extra credit.

Note: Preliminary version of the proposal is graded using the same criteria, but the grade is not recorded, only the grade of the final version will be reflected on your final grade. In other words, the preliminary proposal is only for providing feedback; addressing all of these feedbacks will result in a better score in the final proposal.

Note: Since preliminary proposal will be reviewed by your peer, please keep the preliminary anonymous.

### 2.2. Recommended Structure for Proposals

There is no required structure for your proposal, except you need to have a title for your project. You can choose to follow the structure below, which covers the topics required in the grading criteria:

1. A cool title, or even better, a title with puns. After all, the title is the punch line of the project.
2. Background on the domain: Provide backgrounds on the domain you are targeting:
   - What is the domain you are targeting.
   - Provide a specification for the problem, including examples with expected input and output.
   - How will solving this problem benefit domain experts and/or designers targeting this domain.
   - A brief overview of the challenges in the solution and implementation.
   - A brief overview of your action plan and software structure.
3. Intellectual Merit: In more detail, present several projects in the existing domain, and explain:
   - How your project is different from the existing work.
   - What your project can achieve beyond the existing work.
4. Action Plan: Give detailed explanations of how you are planning to tackle the problem mentioned in the background section. You can choose to include the following considerations:
   - Specifying the syntax if you are implementing a new language, or exposed functions/APIs if you are implementing a library. Backus-Naur form is usually the standard way to specify syntax.
   - Specify the data structure and algorithm used in the implementation that aids in solving the proposed problem.
   - Specify the components of your software design and their connections. You can choose to use dependency graphs and/or flowcharts to explain these connections.
5. Work Allocation: how is the work divided among the members.
6. Limitations and future work: Present the limitation of the approach specified in the action plan, and what are some future extensions possible to address these limitations.

Note: In addition to a clear structure, examples are always helpful to motivate problems and presenting solutions.

## 3. Proposal Peer Review Guide

Each group will be assigned the preliminary proposal of two other groups to review. The review is based on the grading criteria the group will need to provide feedback and comments about:

- Whether the contents of the proposal fulfills the required criteria.
- Contents you find particularly interesting.
- Questions about content that you do not understand.
- Contents that could be improved to better fit the criteria.
- Potential improvements on the goal and action plan.
- Related works that are not present in the proposal.

You do not need to provide a score for each criterion, and your review should be anonymous, as your verbatim review will be provided to the original group to improve their proposals.

The peer review will be graded based on the quality of the feedback and suggestion you provide. More specifically, for a proposal that is brief and unclear, you are expected to provide more questions and suggestions for improvements, and your feedback is expected to cover all the main advancement claimed in the proposal.

## 4. Final Report and Artifact Guide

### 4.1. Project Report

The final report reflects on the project and provide a summary and report on the following aspects of the project:

- Goals Achieved: What problem is your project able to solve? Provide some example of your project working in practice. Which part of the action plan are you able to execute successfully?
- Challenges Remain: Which part of the action plan are you not able to execute successfully? If you switched to a different approach, what were the challenges and design mistakes in the original plan, and how does your new approach solve these challenges?
- Future Works and Road Map: State the problems you are not able to solve within this project and the potential avenues to solve them. Beyond the scope of this project, what are the interesting problems in this domain, whether your work can be extended to solve them, and how do you plan to make such extensions?

Unlike the proposal, final report can be brief, as long as they cover the required points; and the target audience should be programming language experts with minimal exposure to your domain. More specifically, final reports don't need to be accessible to your classmates, but they should not assume deep knowledge of your domain that goes beyond typical undergraduate-level teaching, except within programming languages. If your report requires advance knowledges that are not introduced in your proposal to understand, you will need to explain these knowledges within the final report.

### 4.2. Team Report

Team review is submitted individually, not as a team. In this review you will evaluate the teamwork both as a whole and provides individual review for your teammates, these can include:

- Have you carried out the work division specified in the proposal? If not, specify the change in work division.
- Which part of their performance do you find particularly impressive, and how can you learn from them?
- How can they improve to better foster collaboration?
- Are your teammates respectful of you and your work, are they contributing enough to the project.

Note: This report will not be shown to your teammate unless you give consent.

### 4.3. Artifact

If your project focuses on an implementation, then you will submit your software as an artifact, if your project doesn't require an implementation (i.e. it is a theory project), then you will need to submit a written document as the artifact.

### 4.4. Grading Criteria for Artifacts

Your project will be graded in total of 60 points (12% of your final grade) with 30 points of extra credit, and your grade might be adjusted based on whether you have contributed to the projects as much as your teammates.

For written project, you will be graded on the innovation and effectiveness of your framework, and the depth of your literature reviews. For coding project, your grade will be assigned as follows:

- [30 points] Documentations:
  - [10 points] Code Documentations: Your code needs to have function-level and module-level doc string aligned with the language you use to produce your artifact. For Haskell, the standard doc string format is Haddock. You can also generate standalone documentations as PDFs.
  - [10 points] Evaluation Guide: You will need to provide documentations on how to run your artifact if you elect to build a coding project. In addition, you will need to provide executable examples that demonstrates that you have accomplished your desired goal specified in the final report.
  - [10 points] Project Reports: Your project report needs to provide a fair summary for the state of the project, and have detailed report on team collaboration and work division.
- [30 points] Implementations:
  - [10 points] Modularity: You are expected to neatly organize your code into small functions and modules. You are expected to follow the recommendation on the language of your choosing. For example, functions in most Haskell project would have less than 100 character per line and less than 20 lines. If a function needs to be longer than 20 lines, it will need to be extensively documented with comments.
  - [10 points] Readability: You are expected to follow the style guide for the language of your choosing (PEP8 for python, and this wiki article for Haskell, for example). Additionally, you are expected to use readable variable names in your project, single letter variable names are not acceptable in most cases.
  - [10 points] Innovation and Difficulty: This evaluates the difficulty of your project, and how different is your approaches are from the existing approach. Your project is expected to be either uniquely positioned in your domain or difficult to implement, or both.
- [30 points] Extra Credit:
  - [10 points] Parsing: If you produce a functioning parser for your language via a parser combinator library or a parser generator library depends on their difficulty to use. You will get full 10 points if you implement your own parser combinator library that can output reasonable error message on a parse error.
  - [10 points] Extensive Test Suite: You will get some extra credit if you implemented extensive tests using both standard unit testing and property based testing, and/or demonstrated high test coverage using tools like Haskell Program Coverage.
  - [10 points] Exceptional Innovation: If you have any idea that significantly advances the state of the art either in programming language or your specific domain, and with the comprehensive literature reviews to back up that claim, then you will receive extra credit in this category.

## 5. Additional Resources

### 5.1. SWEET Center For Team Work

Individual and Team Consultations are offered by SWEET fellows who are WPI students, staff, faculty, and alumni with lots of project and teamwork experience, and additional training from WPI experts on effective and equitable teamwork. All Teamwork Support SWEET Center offerings are available for free to WPI undergraduate and graduate students. For more detail: https://www.wpi.edu/academics/global-school/departments-programs-offices/sweet-center.
