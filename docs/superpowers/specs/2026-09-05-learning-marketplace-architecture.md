# NPTOR Learning Marketplace & Certification UX Architecture

## Goal
Create one coherent learning marketplace for Courses, Tracks, Exams, Practice, Wishlist and paid access while preserving existing learning behavior. Students should always understand what a resource is, what is free/paid, what they own, and why something is locked.

## Resource model
- Course: structured lessons, video/article content, lesson quizzes/practice and completion certificate.
- Track: ordered collection of exams used for certification preparation; may have prerequisite/score locks.
- Exam: standalone timed assessment with question count, duration, passing score, attempts and review rules.
- Practice: question-level practice experience, linked to courses/lessons where applicable.

## Public catalog
- Marketplace is the domain-first entry point.
- Common resource cards show type, title, level, key metrics, price/access state and one primary action.
- Access states: Free, Preview, Premium, Purchased, In Progress, Completed, Locked.
- Locked states explain the reason rather than only showing a lock icon.
- Wishlist/shortlist is available on catalog cards and detail pages.

## Course detail
Public course page is sales + curriculum information. Enrolled users get Continue/Review actions and progress. Paid courses show value, price, purchase CTA, preview availability, curriculum, instructor, requirements, outcomes, reviews and FAQ.

## Track detail
Public track page explains the bundle value, included exams, total questions, pricing and savings versus individual exams. Purchased users see a learning dashboard with track progress and each exam's state. Track items support ordered prerequisites and future lock policies such as previous-completed, minimum-score, time delay and admin unlock.

## Exam detail
Exam detail clearly presents question count, duration, passing score, attempts, review behavior, price/access and rules before starting. Locked exams explain prerequisite and provide a path to the required item.

## Commerce
Start with single-resource checkout for Course, Track or Exam. Checkout displays resource, price, discount/coupon, total and payment state. Access is granted only after verified successful payment. Payment return URLs alone never grant entitlement.

## Entitlement
Access should be represented separately from catalog metadata. Entitlements identify user, resource type/id, source, status and optional expiry. Sources may include purchase, admin grant, promotion, bundle or subscription.

## Wishlist
Wishlist is a persistent user feature with Courses, Tracks and Exams. Cards expose add/remove state with accessible labels.

## Student dashboard
Dashboard prioritizes Continue Learning, active Tracks, recent Exam Results, certificates and Wishlist. My Courses, My Tracks and My Exams provide focused views.

## Navigation
Student navigation groups resources into Learn (Courses, Tracks, Practice), Certification (Exams, Study Plan), and Account (Wishlist, Certificates, Profile). Instructor/admin links remain separate.

## Mobile
Marketplace cards become single-column/compact grids. Filters collapse. Course/track learning uses drawers and sticky navigation. Exam attempt mode remains focused and removes marketplace navigation.

## Implementation phases
1. Catalog/resource cards and access-state language.
2. Course detail + learning UX.
3. Track detail/dashboard and lock rules.
4. Exam detail/attempt/result UX.
5. Checkout/order/payment verification and entitlement.
6. Student dashboard, wishlist and cross-resource recommendations.

## Non-goals for phase 1
No payment gateway replacement, no new track locking database schema, no model migration, and no change to existing exam grading or course completion logic until those flows have dedicated tests and design work.
